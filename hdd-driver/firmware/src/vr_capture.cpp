#include "vr_capture.h"

namespace vr {

static HardwareTimer* tim = nullptr;
static volatile uint32_t edges = 0, rejected = 0, last_cap = 0, last_edge_ms = 0;
static volatile uint32_t last_period = 0, prev_period = 0;  // the last two accepted periods
static float thr_mV = 1650;
static int hyst_ = 4, filter_ = 15;
static volatile uint32_t lockout_pct_ = 50, lockout_min_ticks = 0;
static uint32_t tim_hz = 0;

// Snapshot for pulseHz()
static uint32_t snap_edges = 0, snap_cap = 0;

static constexpr uint32_t COMP_EN = 1u << 0, COMP_INMSEL_DAC3_CH1 = 4u << 4,
                          COMP_INPSEL_PA1 = 0u << 8;
static constexpr uint32_t PAUSE_MS = 300;  // a longer gap restarts the lockout (no period yet)

// Rising edge of COMP1 (after TIM2's input filter). Edges closer to the last accepted
// one than the lockout are counted as rejected and otherwise ignored. The lockout uses
// the shorter of the last two accepted periods: after one missed pulse the last period
// is 2T, and 50 % of that would reject the next real pulse, and so on.
static void onCapture() {
  const uint32_t cap = TIM2->CCR1, ms = millis();
  const bool fresh = edges == 0 || ms - last_edge_ms > PAUSE_MS;
  if (!fresh) {
    const uint32_t dt = cap - last_cap;
    uint32_t base = last_period;
    if (prev_period && prev_period < base) base = prev_period;
    uint32_t lock = lockout_min_ticks;
    if (lockout_pct_ && base) lock = max(lock, base / 100u * lockout_pct_);
    if (dt < lock) {
      rejected = rejected + 1;
      return;
    }
    prev_period = last_period;
    last_period = dt;
  } else {
    last_period = prev_period = 0;
  }
  last_cap = cap;
  last_edge_ms = ms;
  edges = edges + 1;
}

// TIM2 CH1 input filter, IC1F = n (RM0440 TIMx_CCMR1): sampling clock and number of
// equal samples needed. CKD = 10, so f_DTS = f_tim / 4.
static float filterUs(int n) {
  static const uint8_t div[16] = {1, 1, 1, 1, 2, 2, 4, 4, 8, 8, 16, 16, 16, 32, 32, 32};
  static const uint8_t num[16] = {1, 2, 4, 8, 6, 8, 6, 8, 6, 8, 5, 6, 8, 5, 6, 8};
  if (n <= 0 || !tim_hz) return 0;
  const float f_sample = n <= 3 ? (float)tim_hz : tim_hz / 4.0f / div[n];
  return num[n] * 1e6f / f_sample;
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

void setFilter(int n) {
  filter_ = constrain(n, 0, 15);
  TIM2->CCMR1 = (TIM2->CCMR1 & ~TIM_CCMR1_IC1F) | ((uint32_t)filter_ << TIM_CCMR1_IC1F_Pos);
}
int filter() { return filter_; }
float filterMicros() { return filterUs(filter_); }

void setLockout(int percent) { lockout_pct_ = constrain(percent, 0, 90); }
int lockout() { return lockout_pct_; }

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
  lockout_min_ticks = (uint32_t)(LOCKOUT_MIN_US * 1e-6f * tim_hz);
  // Input filter on the comparator output: setMode() wrote IC1F = 0, so set it now.
  // CKD = 10 (t_DTS = 4 / f_tim) only affects the filter's sampling clock here.
  TIM2->CR1 = (TIM2->CR1 & ~TIM_CR1_CKD) | TIM_CR1_CKD_1;
  setFilter(filter_);
}

bool comparatorHigh() { return (COMP1->CSR & (1u << 30)) != 0; }

uint32_t edgeCount() { return edges; }
uint32_t rejectedCount() { return rejected; }

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
