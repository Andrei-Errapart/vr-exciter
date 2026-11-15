#include "vr_track.h"

namespace vr_track {

static constexpr float TWO_PI_F = 6.2831853f;
static constexpr float DEG = 57.29578f;
static constexpr int QUARTER = MAGNETS / 4;  // pulses used for the speed estimate
static constexpr float STALE_S = 0.05f;      // no pulse for this long: angle not valid
static constexpr float MIN_MARGIN = 0.15f;   // lock check: best minus second-best correlation

static int pp = 4;
static float fs = 25000.0f;

// ---- ISR state ----
static volatile int k = -1;      // label of the last pulse, -1 = none since begin
static uint32_t t[MAGNETS];      // time of the last pulse of each label (1/256 sample)
static int32_t amp[MAGNETS];     // swing of the last pulse of each label (x16 counts)
static uint32_t ivl[MAGNETS];    // the interval that ended at each label's last pulse (1/256)
static volatile uint32_t cnt = 0, run_cnt = 0;  // pulses since boot / since the last reset
static volatile float omega = 0;  // mechanical rad/s, updated at each pulse
static float pos[MAGNETS];        // mechanical angle of each label, rad (pos[0] = 0)
static float gap[MAGNETS];        // pos[k+1] - pos[k], rad
static float tmpl[MAGNETS];       // interval signature (see signature()), zero mean, unit norm
static volatile bool is_learned = false;
static volatile float offset_e = 0, trim_e = 0, lead_s = 40e-6f;
static volatile float field_e = 0, field_w = 0;

// ---- learning ----
static volatile bool is_learning = false, learn_done = false;
static volatile int learn_left = 0;
static float acc_amp[MAGNETS], acc_iv[MAGNETS], acc_c[MAGNETS], acc_s[MAGNETS];
static uint16_t acc_n[MAGNETS];
static float offset_spread = 0;

// ---- lock check ----
static uint32_t last_check_cnt = 0, n_corrections = 0;
static int pending_shift = 0, last_shift = 0;
static float last_margin = 0, last_corr = 0;
static bool last_ok = false;

// ---- pulse check (onPulse) ----
static volatile uint32_t n_missed = 0, n_extra = 0;
static uint16_t missed_by_label[MAGNETS], extra_by_label[MAGNETS];

static inline float wrap2pi(float a) {
  a = fmodf(a, TWO_PI_F);
  return a < 0 ? a + TWO_PI_F : a;
}
static inline float wrapPi(float a) {
  a = wrap2pi(a);
  return a > PI ? a - TWO_PI_F : a;
}

// The lock's signature: each interval relative to the mean of its two neighbours, minus
// 1, then zero mean and unit norm. The neighbour ratio cancels speed changes, so what is
// left is the magnets' spacing (and per-magnet timing), which does not depend on speed
// or on the detector's filter. (The first lock used the pulse swings, learned at
// 600 rpm; above about 1800 rpm, unfiltered, they no longer matched and the lock made
// hundreds of false corrections.) Returns false if the intervals are not usable.
static bool signature(const float* iv, float* out) {
  float mean = 0;
  for (int i = 0; i < MAGNETS; i++) {
    const float nb = 0.5f * (iv[(i + MAGNETS - 1) % MAGNETS] + iv[(i + 1) % MAGNETS]);
    if (nb <= 0 || iv[i] <= 0) return false;
    out[i] = iv[i] / nb - 1.0f;
    mean += out[i] / MAGNETS;
  }
  float norm = 0;
  for (int i = 0; i < MAGNETS; i++) out[i] -= mean, norm += out[i] * out[i];
  norm = sqrtf(norm);
  if (norm <= 0) return false;
  for (int i = 0; i < MAGNETS; i++) out[i] /= norm;
  return true;
}

static void uniformTables() {
  for (int i = 0; i < MAGNETS; i++) {
    pos[i] = i * TWO_PI_F / MAGNETS;
    gap[i] = TWO_PI_F / MAGNETS;
  }
}

void begin(int pole_pairs, float sample_hz) {
  pp = pole_pairs;
  fs = sample_hz;
  uniformTables();
}

void setPolePairs(int pole_pairs) { pp = pole_pairs; }

void setField(float theta_e, float omega_e) {
  field_e = theta_e;
  field_w = omega_e;
}

void onPulse(uint32_t t256, int32_t swing16, uint32_t now256) {
  // A pause longer than STALE_S restarts the speed history (not the labels).
  const int prev = k;
  if (prev >= 0 && (int32_t)(t256 - t[prev]) > (int32_t)(STALE_S * 4 * fs * 256)) run_cnt = 0;
  int kk = prev < 0 ? 0 : (prev + 1) % MAGNETS;
  const uint32_t iv256 = prev >= 0 ? t256 - t[prev] : 0;
  bool skipped = false;
  // Check the pulse against the expected interval to the next magnet (its learned gap
  // at the current speed). At 1800-2050 rpm about one pulse in 3600 was missed or added,
  // and the lock check fixed the labels only up to two revolutions later (bench run
  // 2026-11-15_1828). Far too early: a spurious pulse, ignored. About two gaps late: one
  // was missed, so the labels move on by two at once.
  if (prev >= 0 && run_cnt > QUARTER && omega > 0) {
    const float dt = (float)iv256 / 256.0f / fs;
    const int k2 = (prev + 2) % MAGNETS;
    const float e1 = gap[prev] / omega, e2 = e1 + gap[kk] / omega;
    if (dt < 0.5f * e1) {
      n_extra = n_extra + 1;
      extra_by_label[kk]++;
      return;
    }
    if (dt > 0.5f * (e1 + e2) && dt < e2 + 0.5f * gap[k2] / omega) {
      n_missed = n_missed + 1;
      missed_by_label[kk]++;
      t[kk] = t[prev] + (uint32_t)(e1 * fs * 256.0f);  // where the missed one should have been
      ivl[kk] = 0;  // unknown: the lock check waits for a full revolution again
      kk = k2;
      skipped = true;
    }
  }
  t[kk] = t256;
  amp[kk] = swing16;
  ivl[kk] = (run_cnt > 0 && !skipped) ? iv256 : 0;  // no interval across a pause or a skip
  k = kk;
  cnt = cnt + 1;
  run_cnt = run_cnt + 1;
  if (run_cnt > QUARTER) {
    const int k0 = (kk + MAGNETS - QUARTER) % MAGNETS;
    const float dth = wrap2pi(pos[kk] - pos[k0]);
    const float dt = (float)(t256 - t[k0]) / 256.0f / fs;
    if (dt > 0) omega = dth / dt;
  }
  if (is_learning && run_cnt > 1) {
    acc_amp[kk] += swing16;
    acc_iv[kk] += iv256 / 256.0f;
    // the field angle applied at the pulse time (computed angles take effect a lead later)
    const float back = (float)(int32_t)(now256 - t256) / 256.0f / fs + lead_s;
    const float th = field_e - field_w * back;
    acc_c[kk] += cosf(th);
    acc_s[kk] += sinf(th);
    acc_n[kk]++;
    if (--learn_left <= 0) {
      is_learning = false;
      learn_done = true;
    }
  }
}

bool angleValid(uint32_t now256) {
  const int kk = k;
  if (kk < 0 || run_cnt <= QUARTER) return false;
  return (float)(int32_t)(now256 - t[kk]) / 256.0f / fs < STALE_S;
}

static float mechAngle(uint32_t now256) {
  const int kk = k;
  if (kk < 0) return 0;
  const float w = omega;
  float adv = w * (float)(int32_t)(now256 - t[kk]) / 256.0f / fs;
  const float lim = 1.5f * gap[kk];
  if (adv > lim) adv = lim;
  if (adv < 0) adv = 0;
  return pos[kk] + adv;
}

float electricalAngle(uint32_t now256) {
  return wrap2pi(pp * mechAngle(now256) + offset_e + trim_e + pp * omega * lead_s);
}

float fieldLagDeg(uint32_t now256) {
  if (!is_learned) return 0;
  // field_e is the angle computed now; it is applied a lead later, like electricalAngle().
  // The field's own vector is at field_e + 90 degrees (see finishLearning), so this is
  // the open-loop load angle: how far the field leads the magnet.
  return wrapPi(field_e + PI / 2 + field_w * lead_s - electricalAngle(now256) + trim_e) * DEG;
}

bool startLearning(int revolutions) {
  if (is_learning) return false;
  noInterrupts();
  for (int i = 0; i < MAGNETS; i++) acc_amp[i] = acc_iv[i] = acc_c[i] = acc_s[i] = 0, acc_n[i] = 0;
  learn_done = false;
  learn_left = constrain(revolutions, 3, 50) * MAGNETS;
  is_learning = true;
  interrupts();
  return true;
}

static void finishLearning() {
  float iv[MAGNETS], a[MAGNETS], p[MAGNETS], g[MAGNETS], tm[MAGNETS];
  float total = 0, amean = 0;
  for (int i = 0; i < MAGNETS; i++) {
    const float n = acc_n[i] ? acc_n[i] : 1;
    iv[i] = acc_iv[i] / n;
    a[i] = acc_amp[i] / n;
    total += iv[i];
    amean += a[i] / MAGNETS;
  }
  if (total <= 0) return;
  // acc_iv[i] is the interval that ends at label i, so label i sits that far past i-1.
  p[0] = 0;
  for (int i = 1; i < MAGNETS; i++) p[i] = p[i - 1] + iv[i] / total * TWO_PI_F;
  for (int i = 0; i < MAGNETS; i++) g[i] = (i + 1 < MAGNETS ? p[i + 1] : TWO_PI_F) - p[i];
  (void)amean;
  if (!signature(iv, tm)) return;
  // electrical offset: circular mean over labels of (field angle - pp x label angle)
  float sc = 0, ss = 0;
  float x[MAGNETS];
  for (int i = 0; i < MAGNETS; i++) {
    x[i] = atan2f(acc_s[i], acc_c[i]) - pp * p[i];
    sc += cosf(x[i]);
    ss += sinf(x[i]);
  }
  // SimpleFOC's setPhaseVoltage(Uq, 0, a) puts the voltage at a + 90 degrees. In open
  // loop at light load the magnet lines up with that vector (lagging only by the small
  // load angle), so the rotor's electrical angle is the field angle + 90 degrees.
  // (Without the 90, closing the loop put the voltage along the magnet: no torque.)
  const float mean_x = atan2f(ss, sc);
  const float off = mean_x + PI / 2;
  float spread = 0;
  for (int i = 0; i < MAGNETS; i++) spread += sq(wrapPi(x[i] - mean_x));
  offset_spread = sqrtf(spread / MAGNETS) * DEG;
  noInterrupts();
  for (int i = 0; i < MAGNETS; i++) pos[i] = p[i], gap[i] = g[i], tmpl[i] = tm[i];
  offset_e = off;
  is_learned = true;
  interrupts();
  pending_shift = last_shift = 0;
  last_check_cnt = cnt;
}

static void lockCheck() {
  if (!is_learned || is_learning) return;
  const uint32_t c = cnt;
  if (c - last_check_cnt < (uint32_t)MAGNETS) return;
  last_check_cnt = c;
  float iv[MAGNETS], m[MAGNETS];
  noInterrupts();
  for (int i = 0; i < MAGNETS; i++) iv[i] = ivl[i] / 256.0f;
  interrupts();
  if (!signature(iv, m)) return;  // an interval missing (after a pause): next revolution
  int best = 0;
  float c1 = -2, c2 = -2;
  for (int s = 0; s < MAGNETS; s++) {
    float cc = 0;
    for (int j = 0; j < MAGNETS; j++) cc += m[j] * tmpl[(j + s) % MAGNETS];
    if (cc > c1) c2 = c1, c1 = cc, best = s;
    else if (cc > c2) c2 = cc;
  }
  last_corr = c1;
  last_margin = c1 - c2;
  last_shift = best > MAGNETS / 2 ? best - MAGNETS : best;
  last_ok = best == 0 && last_margin >= MIN_MARGIN;
  if (best == 0 || last_margin < MIN_MARGIN) {
    pending_shift = 0;
    return;
  }
  if (pending_shift != best) {
    pending_shift = best;
    return;
  }
  // Seen twice: our label j is magnet j + best. Relabel.
  noInterrupts();
  uint32_t t2[MAGNETS], i2[MAGNETS];
  int32_t a2[MAGNETS];
  for (int j = 0; j < MAGNETS; j++) {
    const int jj = (j + best) % MAGNETS;
    t2[jj] = t[j], a2[jj] = amp[j], i2[jj] = ivl[j];
  }
  for (int j = 0; j < MAGNETS; j++) t[j] = t2[j], amp[j] = a2[j], ivl[j] = i2[j];
  k = (k + best) % MAGNETS;
  run_cnt = 0;  // the speed history spans the slip: restart it
  interrupts();
  n_corrections++;
  pending_shift = 0;
}

void poll() {
  if (learn_done) {
    learn_done = false;
    finishLearning();
  }
  lockCheck();
}

bool learning() { return is_learning; }
bool learned() { return is_learned; }
bool locked() { return is_learned && last_ok && pending_shift == 0; }
float speedRpm() { return omega * 60.0f / TWO_PI_F; }
uint32_t pulseCount() { return cnt; }
int label() { return k; }
int lastShift() { return last_shift; }
float lastMargin() { return last_margin; }
float lastCorrelation() { return last_corr; }
uint32_t missedPulses() { return n_missed; }
uint32_t extraPulses() { return n_extra; }
int worstLabel(bool missed, uint32_t* count) {
  const uint16_t* a = missed ? missed_by_label : extra_by_label;
  int w = 0;
  for (int i = 1; i < MAGNETS; i++) if (a[i] > a[w]) w = i;
  if (count) *count = a[w];
  return w;
}
uint32_t corrections() { return n_corrections; }
float offsetDeg() { return offset_e * DEG; }
float offsetSpreadDeg() { return offset_spread; }
void setTrimDeg(float deg) { trim_e = constrain(deg, -180.0f, 180.0f) / DEG; }
float trimDeg() { return trim_e * DEG; }
void setLeadUs(float us) { lead_s = constrain(us, 0.0f, 500.0f) * 1e-6f; }
float leadUs() { return lead_s * 1e6f; }

}  // namespace vr_track
