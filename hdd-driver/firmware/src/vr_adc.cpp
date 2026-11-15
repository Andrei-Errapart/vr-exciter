#include "vr_adc.h"
#include "fast_adc.h"

namespace vr_adc {

static constexpr int VR_CH = 2;  // ADC2_IN2 = PA1
static constexpr uint32_t N = 1024;  // circular buffer: about 41 ms at 25 kHz
static constexpr float DECAY_S = 0.05f;
static constexpr float COUNTS_PER_MV = 4095.0f / 3300.0f;
static constexpr int32_t SCALE = 16;  // the filter keeps 4 fractional bits

static uint16_t buf[N];
static bool active = false;
static float fs = 25000;          // sample rate
static uint32_t rd = 0;           // next buffer index to process
static uint32_t idx = 0;          // absolute index of the next sample
static uint32_t last_poll_ms = 0, overrun_count = 0;
static uint32_t decay_samples = 1250;

// Settings
static int32_t floor16 = (int32_t)(10.0f * COUNTS_PER_MV * SCALE);  // standstill noise: 6-7 mV pp
static int32_t hyst_pct = 30;
// Low-pass y += (x - y) / 2^shift. Its time constant (2^shift samples) is kept at most a
// tenth of the pulse spacing: at 600 rpm a fixed 1/8 smoothed away the weak magnet's
// pulse (590 instead of 600 pulses/s), 1/4 counted all 60. max_shift (YA) applies at
// low speed and standstill, where the noise needs it.
static int32_t max_shift = 3;
static int32_t cur_shift = 3;
static uint32_t iv_last = 0, iv_prev = 0;  // the last two pulse intervals, 1/256 sample

// Detector state
static uint16_t m1 = 0, m2 = 0;          // the two previous raw samples
static int32_t y16 = 0, y_prev16 = 0;    // filtered signal, x16
static bool primed = false, rising = true, have_peak = false, have_trough = false, armed = false;
static int32_t ext16 = 0, peak16 = 0, trough16 = 0, mid16 = 0, pp16 = 0;
static uint32_t last_extreme_idx = 0;

// Results: pulse times in 1/256 sample (wraps after 11 min; only differences are used)
static uint32_t pulses = 0, last_pulse_t256 = 0, last_pulse_ms = 0;
static uint32_t snap_pulses = 0, snap_t256 = 0;

static inline uint16_t median3(uint16_t a, uint16_t b, uint16_t c) {
  const uint16_t lo = a < b ? a : b, hi = a < b ? b : a;
  return c < lo ? lo : (c > hi ? hi : c);
}

static void resetDetector() {
  primed = false;
  rising = true;
  have_peak = have_trough = armed = false;
  pp16 = 0;
  iv_last = iv_prev = 0;
  cur_shift = max_shift;
}

static inline void pulse(uint32_t t256) {
  if (pulses) {
    iv_prev = iv_last;
    iv_last = t256 - last_pulse_t256;
    // The shorter of the last two intervals, so one missed pulse does not tighten it.
    const uint32_t p = (iv_prev && iv_prev < iv_last) ? iv_prev : iv_last;
    int32_t s = 0;
    while (s < max_shift && (10u << (s + 1)) * 256u <= p) s++;  // 2^s <= p / 10 samples
    cur_shift = s;
  }
  last_pulse_t256 = t256;
  last_pulse_ms = millis();
  pulses++;
}

// Sample number i (absolute index).
static void onSample(uint16_t raw, uint32_t i) {
  if (!primed) {
    m1 = m2 = raw;
    y16 = y_prev16 = ext16 = (int32_t)raw * SCALE;
    last_extreme_idx = i;
    primed = true;
    return;
  }
  const uint16_t med = median3(raw, m1, m2);
  m2 = m1;
  m1 = raw;
  y16 += ((int32_t)med * SCALE - y16) / (1 << cur_shift);
  const int32_t y = y16;
  int32_t h = pp16 * hyst_pct / 100;
  if (h < floor16) h = floor16;

  if (rising) {
    if (armed && y_prev16 < mid16 && y >= mid16) {
      // between samples i-1 and i, linearly
      const uint32_t frac256 = (uint32_t)(256 * (mid16 - y_prev16) / (y - y_prev16));
      pulse(((i - 1) << 8) + frac256);
      armed = false;
    }
    if (y > ext16) {
      ext16 = y;
    } else if (y < ext16 - h) {  // peak confirmed
      peak16 = ext16;
      if (have_trough) pp16 += (peak16 - trough16 - pp16) / 4;
      have_peak = true;
      rising = false;
      armed = false;
      ext16 = y;
      last_extreme_idx = i;
    }
  } else {
    if (y < ext16) {
      ext16 = y;
    } else if (y > ext16 + h) {  // trough confirmed
      trough16 = ext16;
      have_trough = true;
      rising = true;
      ext16 = y;
      last_extreme_idx = i;
      if (have_peak) {
        mid16 = (peak16 + trough16) / 2;
        if (y >= mid16) pulse(i << 8);  // already past the midpoint (h >= half the swing)
        else armed = true;
      }
    }
  }
  if (i - last_extreme_idx > decay_samples) {  // no pulses: let the hysteresis come down
    pp16 /= 2;
    cur_shift = max_shift;
    last_extreme_idx = i;
  }
  y_prev16 = y;
}

static float tim1UpdateHz() {
  uint32_t clk = HAL_RCC_GetPCLK2Freq();
  if ((RCC->CFGR & RCC_CFGR_PPRE2) >= RCC_CFGR_PPRE2_2) clk *= 2;
  const float psc = TIM1->PSC + 1.0f, rcr = TIM1->RCR + 1.0f;
  // Center-aligned: ARR ticks per half period, an update every RCR+1 half periods.
  if (TIM1->CR1 & TIM_CR1_CMS) return clk / (psc * TIM1->ARR * rcr);
  return clk / (psc * (TIM1->ARR + 1.0f) * rcr);
}

static inline uint32_t writePos() { return (N - DMA1_Channel3->CNDTR) % N; }

void poll() {
  if (!active) return;
  const uint32_t ms = millis();
  // The buffer lasts N / fs (41 ms at 25 kHz). Away longer, samples were overwritten.
  if (ms - last_poll_ms > (uint32_t)(0.8f * N * 1000.0f / fs)) {
    idx += (uint32_t)((ms - last_poll_ms) * fs / 1000.0f);
    rd = writePos();
    resetDetector();
    overrun_count++;
    last_poll_ms = ms;
    return;
  }
  last_poll_ms = ms;
  const uint32_t wr = writePos();
  while (rd != wr) {
    onSample(buf[rd], idx);
    rd = (rd + 1) % N;
    idx++;
  }
}

void begin() {
  __HAL_RCC_DMAMUX1_CLK_ENABLE();
  __HAL_RCC_DMA1_CLK_ENABLE();
  // TIM1 TRGO = update event (MMS = 010): with SimpleFOC's RCR = 1, once per PWM period.
  TIM1->CR2 = (TIM1->CR2 & ~TIM_CR2_MMS) | TIM_CR2_MMS_1;
  resume();
}

void pause() {
  active = false;
  if (ADC2->CR & ADC_CR_ADSTART) {
    ADC2->CR |= ADC_CR_ADSTP;
    while (ADC2->CR & ADC_CR_ADSTP) {}
  }
  DMA1_Channel3->CCR = 0;
  DMAMUX1_Channel2->CCR = 0;
  ADC2->CFGR = ADC_CFGR_JQDIS;  // fast_adc's setting: no regular trigger, no DMA
}

void resume() {
  fs = tim1UpdateHz();
  decay_samples = (uint32_t)(DECAY_S * fs);
  // ADC2 must be idle for the setup; fast_adc's injected I_B reads are synchronous.
  while (ADC2->CR & (ADC_CR_ADSTART | ADC_CR_JADSTART)) {}
  fast_adc::setSampleTime(ADC2, VR_CH, fast_adc::SMP_47_5);
  ADC2->SQR1 = (uint32_t)VR_CH << ADC_SQR1_SQ1_Pos;  // one conversion
  // Triggered by TIM1_TRGO (rising), DMA in circular mode, overrun overwrites, and the
  // injected queue stays disabled for fast_adc's I_B.
  ADC2->CFGR = ADC_CFGR_JQDIS | ADC_EXTERNALTRIG_T1_TRGO | ADC_CFGR_EXTEN_0 | ADC_CFGR_DMAEN |
               ADC_CFGR_DMACFG | ADC_CFGR_OVRMOD;
  DMA1_Channel3->CCR = 0;
  DMAMUX1_Channel2->CCR = DMA_REQUEST_ADC2;
  DMA1_Channel3->CPAR = (uint32_t)&ADC2->DR;
  DMA1_Channel3->CMAR = (uint32_t)buf;
  DMA1_Channel3->CNDTR = N;
  DMA1->IFCR = DMA_IFCR_CGIF3;
  // peripheral -> memory, 16 bit both sides, memory increment, circular
  DMA1_Channel3->CCR = DMA_CCR_MINC | DMA_CCR_CIRC | DMA_CCR_PSIZE_0 | DMA_CCR_MSIZE_0 | DMA_CCR_EN;
  rd = 0;
  resetDetector();
  last_poll_ms = millis();
  ADC2->ISR = ADC_ISR_EOC | ADC_ISR_EOS | ADC_ISR_OVR;
  ADC2->CR |= ADC_CR_ADSTART;  // armed: converts on each trigger
  active = true;
}

void setHystPercent(int pct) { hyst_pct = constrain(pct, 5, 45); }
void setLowPassMaxShift(int shift) { max_shift = constrain(shift, 0, 5); cur_shift = min(cur_shift, max_shift); }
int lowPassMaxShift() { return max_shift; }
int lowPassShift() { return cur_shift; }
int hystPercent() { return hyst_pct; }
void setFloorMv(float mV) { floor16 = (int32_t)(constrain(mV, 1.0f, 100.0f) * COUNTS_PER_MV * SCALE); }
float floorMv() { return floor16 / (COUNTS_PER_MV * SCALE); }

uint32_t pulseCount() { return pulses; }
uint32_t sampleCount() { return idx; }
float sampleHz() { return fs; }
uint32_t overruns() { return overrun_count; }
float ppMv() { return pp16 / (COUNTS_PER_MV * SCALE); }
float levelMv() { return y16 / (COUNTS_PER_MV * SCALE); }

float pulseHz(uint32_t timeout_ms) {
  const uint32_t dp = pulses - snap_pulses, dt256 = last_pulse_t256 - snap_t256;
  snap_pulses = pulses;
  snap_t256 = last_pulse_t256;
  if (millis() - last_pulse_ms > timeout_ms || dp == 0 || dt256 == 0) return 0;
  // The first interval after a pause spans the gap; that is fine for a rate.
  return (float)dp * fs * 256.0f / (float)dt256;
}

}  // namespace vr_adc
