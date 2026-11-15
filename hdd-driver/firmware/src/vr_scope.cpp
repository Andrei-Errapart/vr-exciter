#include "vr_scope.h"
#include "fast_adc.h"
#include "vr_capture.h"

namespace vr_scope {

static uint32_t adc_buf[MAX_SAMPLES];   // ADC12 CDR: bits 0..15 ADC1 (VR), 16..31 ADC2 (I_B)
static uint16_t pin_buf[MAX_SAMPLES];   // GPIOA->IDR
static int count = 0;

static constexpr int VR_CH = 2, IB_CH = 17;
static constexpr uint32_t DUAL_REG_SIMULT = 6u;  // ADC_CCR DUAL = 00110
static constexpr uint32_t MDMA_12BIT = 2u;       // ADC_CCR MDMA = 10

static uint32_t tim6ClockHz() {
  uint32_t pclk1 = HAL_RCC_GetPCLK1Freq();
  return (RCC->CFGR & RCC_CFGR_PPRE1) >= RCC_CFGR_PPRE1_2 ? 2 * pclk1 : pclk1;
}

static void dmaChannel(DMA_Channel_TypeDef* ch, DMAMUX_Channel_TypeDef* mux, uint32_t request,
                       volatile void* periph, void* mem, uint32_t n, uint32_t size_bits) {
  ch->CCR = 0;
  mux->CCR = request;
  ch->CPAR = (uint32_t)periph;
  ch->CMAR = (uint32_t)mem;
  ch->CNDTR = n;
  // peripheral -> memory, memory increment, PSIZE = MSIZE = size_bits (0 = 8, 1 = 16, 2 = 32 bit)
  ch->CCR = DMA_CCR_MINC | (size_bits << DMA_CCR_PSIZE_Pos) | (size_bits << DMA_CCR_MSIZE_Pos) | DMA_CCR_EN;
}

static void restoreAdcs() {
  if (ADC1->CR & ADC_CR_ADSTART) {
    ADC1->CR |= ADC_CR_ADSTP;
    while (ADC1->CR & ADC_CR_ADSTP) {}
  }
  if (ADC2->CR & ADC_CR_ADSTART) {
    ADC2->CR |= ADC_CR_ADSTP;
    while (ADC2->CR & ADC_CR_ADSTP) {}
  }
  ADC12_COMMON->CCR &= ~(ADC_CCR_DUAL | ADC_CCR_MDMA | ADC_CCR_DMACFG);
  ADC1->CFGR = 0;  // as fast_adc::begin(): 12 bit, software trigger, single conversion
  ADC2->CFGR = 0;
  fast_adc::setSampleTime(ADC1, VR_CH, fast_adc::SMP_640_5);
  fast_adc::setSampleTime(ADC2, IB_CH, fast_adc::SMP_24_5);
  ADC1->ISR = ADC_ISR_EOC | ADC_ISR_EOS | ADC_ISR_OVR | ADC_ISR_EOSMP;
  ADC2->ISR = ADC_ISR_EOC | ADC_ISR_EOS | ADC_ISR_OVR | ADC_ISR_EOSMP;
}

Result capture(float interval_us, int n) {
  n = constrain(n, 1, MAX_SAMPLES);
  const uint32_t clk = tim6ClockHz();
  uint32_t period = (uint32_t)(max(interval_us, MIN_INTERVAL_US) * (clk / 1e6f) + 0.5f);
  period = constrain(period, 2u, 65536u);
  const float actual_us = period * 1e6f / clk;

  __HAL_RCC_DMAMUX1_CLK_ENABLE();
  __HAL_RCC_DMA1_CLK_ENABLE();
  __HAL_RCC_TIM6_CLK_ENABLE();

  // TIM6: update every 'period' clocks; TRGO = update (ADC trigger); DMA request on update.
  TIM6->CR1 = 0;
  TIM6->PSC = 0;
  TIM6->ARR = period - 1;
  TIM6->CNT = 0;
  TIM6->CR2 = TIM_CR2_MMS_1;  // MMS = 010: update -> TRGO
  TIM6->EGR = TIM_EGR_UG;     // load PSC/ARR now
  TIM6->SR = 0;
  TIM6->DIER = TIM_DIER_UDE;

  // ADCs: equal sample times (simultaneous mode), ADC1 triggered by TIM6 TRGO on the
  // rising edge, ADC2 follows as slave; overrun overwrites rather than stalling the DMA.
  fast_adc::setSampleTime(ADC1, VR_CH, fast_adc::SMP_47_5);
  fast_adc::setSampleTime(ADC2, IB_CH, fast_adc::SMP_47_5);
  ADC1->SQR1 = (uint32_t)VR_CH << ADC_SQR1_SQ1_Pos;
  ADC2->SQR1 = (uint32_t)IB_CH << ADC_SQR1_SQ1_Pos;
  ADC1->ISR = ADC_ISR_EOC | ADC_ISR_EOS | ADC_ISR_OVR | ADC_ISR_EOSMP;
  ADC2->ISR = ADC_ISR_EOC | ADC_ISR_EOS | ADC_ISR_OVR | ADC_ISR_EOSMP;
  ADC12_COMMON->CCR = (ADC12_COMMON->CCR & ~(ADC_CCR_DUAL | ADC_CCR_MDMA | ADC_CCR_DMACFG)) |
                      (DUAL_REG_SIMULT << ADC_CCR_DUAL_Pos) | (MDMA_12BIT << ADC_CCR_MDMA_Pos);
  ADC1->CFGR = ADC_EXTERNALTRIG_T6_TRGO | ADC_CFGR_EXTEN_0 | ADC_CFGR_OVRMOD;
  ADC2->CFGR = ADC_CFGR_OVRMOD;

  DMA1->IFCR = DMA_IFCR_CGIF1 | DMA_IFCR_CGIF2;
  dmaChannel(DMA1_Channel1, DMAMUX1_Channel0, DMA_REQUEST_ADC1, &ADC12_COMMON->CDR, adc_buf, n, 2);
  dmaChannel(DMA1_Channel2, DMAMUX1_Channel1, DMA_REQUEST_TIM6_UP, &GPIOA->IDR, pin_buf, n, 1);

  ADC1->CR |= ADC_CR_ADSTART;  // armed: converts on each trigger (master starts the slave)
  const uint32_t e0 = vr::edgeCount();
  TIM6->CR1 = TIM_CR1_CEN;

  const uint32_t timeout_ms = (uint32_t)(n * actual_us / 1000.0f) + 20;
  const uint32_t start = millis();
  while ((DMA1_Channel1->CNDTR || DMA1_Channel2->CNDTR) && millis() - start < timeout_ms) {}
  const bool done = DMA1_Channel1->CNDTR == 0 && DMA1_Channel2->CNDTR == 0;

  TIM6->CR1 = 0;
  TIM6->DIER = 0;
  const uint32_t edges = vr::edgeCount() - e0;
  DMA1_Channel1->CCR = 0;
  DMA1_Channel2->CCR = 0;
  DMAMUX1_Channel0->CCR = 0;
  DMAMUX1_Channel1->CCR = 0;
  restoreAdcs();

  count = done ? n : 0;
  return Result{count, actual_us, edges};
}

void print(Stream& out) {
  char line[24];
  for (int i = 0; i < count; i++) {
    const uint32_t a = adc_buf[i];
    int len = snprintf(line, sizeof line, "%u %u %u\n", (unsigned)(a & 0x0FFFu),
                       (unsigned)((a >> 16) & 0x0FFFu), (unsigned)((pin_buf[i] >> 8) & 7u));
    out.write(line, len);
  }
}

}  // namespace vr_scope
