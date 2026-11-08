#include "vr_capture.h"

namespace vr {

static HardwareTimer* tim = nullptr;
static volatile uint32_t edges = 0, last_cap = 0, last_edge_ms = 0;
static float thr_mV = 1650;
static int hyst_ = 4;
static uint32_t tim_hz = 0;

// Snapshot for pulseHz()
static uint32_t snap_edges = 0, snap_cap = 0;

static constexpr uint32_t COMP_EN = 1u << 0, COMP_INMSEL_DAC3_CH1 = 4u << 4,
                          COMP_INPSEL_PA1 = 0u << 8;

static void onCapture() {
  last_cap = TIM2->CCR1;
  last_edge_ms = millis();
  edges = edges + 1;
}

static void writeComp() {
  COMP1->CSR = COMP_INPSEL_PA1 | COMP_INMSEL_DAC3_CH1 | ((uint32_t)hyst_ << 16) | COMP_EN;
}

void setThreshold(float mV) {
  thr_mV = constrain(mV, 0.0f, 3300.0f);
  DAC3->DHR12R1 = (uint32_t)(thr_mV / 3300.0f * 4095.0f + 0.5f);
}

void setHysteresis(int hyst) {
  hyst_ = constrain(hyst, 0, 7);
  writeComp();
}

float threshold() { return thr_mV; }
int hysteresis() { return hyst_; }

void begin(float threshold_mV, int hyst) {
  pinMode(PA1, INPUT_ANALOG);

  // DAC3 CH1 as an internal-only reference: MODE1 = 011 (on-chip peripherals,
  // buffer disabled), so nothing is driven on PB1.
  __HAL_RCC_DAC3_CLK_ENABLE();
  DAC3->CR &= ~DAC_CR_EN1;
  DAC3->MCR = (DAC3->MCR & ~DAC_MCR_MODE1) | (3u << DAC_MCR_MODE1_Pos);
  setThreshold(threshold_mV);
  DAC3->CR |= DAC_CR_EN1;
  delayMicroseconds(20);  // DAC wake-up

  __HAL_RCC_SYSCFG_CLK_ENABLE();  // COMP shares the SYSCFG clock enable
  hyst_ = constrain(hyst, 0, 7);
  writeComp();
  delayMicroseconds(10);

  // TIM2: free-running 32-bit counter at the timer clock, capture on CH1
  // rising edge, with the input taken from comp1_out.
  tim = new HardwareTimer(TIM2);
  tim->setMode(1, TIMER_INPUT_CAPTURE_RISING, NC);
  tim->setPrescaleFactor(1);
  tim->setOverflow(0xFFFFFFFFu, TICK_FORMAT);
  TIM2->TISEL = 1;  // TI1SEL = tim_ti1_in1 = comp1_out
  tim->attachInterrupt(1, onCapture);
  tim->resume();
  tim_hz = tim->getTimerClkFreq();
}

bool comparatorHigh() { return (COMP1->CSR & (1u << 30)) != 0; }

uint32_t edgeCount() { return edges; }

float pulseHz(uint32_t timeout_ms) {
  noInterrupts();
  uint32_t e = edges, c = last_cap, ms = last_edge_ms;
  interrupts();
  uint32_t de = e - snap_edges, dc = c - snap_cap;
  snap_edges = e;
  snap_cap = c;
  if (millis() - ms > timeout_ms) return 0;
  if (de == 0) return 0;  // window without an edge, wait for the timeout
  // The first interval after a pause spans the gap; that is fine for a rate.
  return (float)de * (float)tim_hz / (float)dc;
}

}  // namespace vr
