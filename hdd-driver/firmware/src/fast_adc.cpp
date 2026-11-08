#include "fast_adc.h"

namespace fast_adc {

static constexpr uint32_t SMP_24_5 = 3, SMP_640_5 = 7;

static void setSampleTime(ADC_TypeDef* adc, int ch, uint32_t smp) {
  volatile uint32_t* reg = ch < 10 ? &adc->SMPR1 : &adc->SMPR2;
  int pos = 3 * (ch < 10 ? ch : ch - 10);
  *reg = (*reg & ~(7u << pos)) | (smp << pos);
}

static void bringUp(ADC_TypeDef* adc) {
  adc->CR &= ~ADC_CR_DEEPPWD;
  adc->CR |= ADC_CR_ADVREGEN;
  delayMicroseconds(30);  // regulator start-up (20 us typ)
  adc->CR &= ~ADC_CR_ADCALDIF;  // single-ended calibration
  adc->CR |= ADC_CR_ADCAL;
  while (adc->CR & ADC_CR_ADCAL) {}
  delayMicroseconds(1);
  adc->ISR = ADC_ISR_ADRDY;
  adc->CR |= ADC_CR_ADEN;
  while (!(adc->ISR & ADC_ISR_ADRDY)) {}
  adc->CFGR = 0;  // 12 bit, right aligned, software trigger, single conversion
  adc->SQR1 = 0;  // one conversion in the sequence
}

void begin() {
  __HAL_RCC_ADC12_CLK_ENABLE();
  ADC12_COMMON->CCR = (ADC12_COMMON->CCR & ~ADC_CCR_CKMODE) | ADC_CCR_CKMODE;  // HCLK / 4 = 42.5 MHz
  bringUp(ADC1);
  bringUp(ADC2);
  // High-impedance sources (VM divider 9 kohm, VR 22 kohm) get the longest sample time.
  setSampleTime(ADC1, 1, SMP_640_5);
  setSampleTime(ADC1, 2, SMP_640_5);
  setSampleTime(ADC1, 3, SMP_24_5);
  setSampleTime(ADC1, 4, SMP_24_5);
  setSampleTime(ADC2, 17, SMP_24_5);
}

uint16_t read1(int ch) {
  ADC1->SQR1 = (uint32_t)ch << ADC_SQR1_SQ1_Pos;
  ADC1->CR |= ADC_CR_ADSTART;
  while (!(ADC1->ISR & ADC_ISR_EOC)) {}
  return ADC1->DR;
}

void readPair(int ch1, uint16_t& v1, uint16_t& v2) {
  ADC1->SQR1 = (uint32_t)ch1 << ADC_SQR1_SQ1_Pos;
  ADC2->SQR1 = 17u << ADC_SQR1_SQ1_Pos;
  ADC1->CR |= ADC_CR_ADSTART;
  ADC2->CR |= ADC_CR_ADSTART;
  while (!(ADC1->ISR & ADC_ISR_EOC)) {}
  while (!(ADC2->ISR & ADC_ISR_EOC)) {}
  v1 = ADC1->DR;
  v2 = ADC2->DR;
}

}  // namespace fast_adc
