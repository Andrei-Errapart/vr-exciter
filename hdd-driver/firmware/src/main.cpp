// hdd-driver firmware, bring-up version.
//
// Open-loop velocity control of the HDD spindle motor through the SimpleFOC
// Mini (DRV8313). The driver stays OFF after reset; spin it with the serial
// commands below (USB-C, 115200 8N1, any terminal, newline terminated).
//
//   E1 / E0     enable / disable the driver
//   R<rpm>      target speed in rpm (mechanical), e.g. R300. Negative reverses.
//   A<rpm/s>    acceleration (from standstill up to ACCEL_BREAK_RPM), e.g. A5
//   F<rpm/s>    acceleration above ACCEL_BREAK_RPM (0 = same as A). The rotor pulls in
//               slowly from standstill but tolerates faster ramps once it is locked.
//   V<volts>    phase voltage limit / cap (max MAX_VOLTAGE)
//   I<amps>     current regulation: the voltage is adjusted (up to the V cap) to hold
//               this torque current while speed, and with it the back-EMF, rises.
//               I0 = off (fixed voltage V).
//   J<amps>     start boost: this current from standstill, tapering linearly to I at
//               ACCEL_BREAK_RPM. Helps the rotor pull in. 0 = off.
//   P<n>        motor pole pairs (default POLE_PAIRS)
//   T<ms>       telemetry period, 0 = off
//   S           print status
//   D           (diagnostic, during an alignment hold) histogram of raw ia/ib samples
//   B           reboot into the ROM DFU bootloader (for flashing without the BOOT0 button)
//   L<ms>       rotor alignment hold before the ramp (default ALIGN_MS, 0 = skip)
//
// VR pickup B, two detectors running side by side, reported as vrpm / vpps (the selected
// one), apps (ADC detector, vr_adc.h) and cpps (comparator, vr_capture.h):
//   YN<n>       VR pulses per revolution (default VR_PULSES_PER_REV)
//   YS<0|1>     source for vrpm / vpps and the stall guard: 1 = ADC detector (default),
//               0 = comparator
//   YP<5..45>   ADC detector: hysteresis in % of the recent peak-to-peak (default 30)
//   YM<mV>      ADC detector: smallest hysteresis (default 10)
//   YA<0..5>    ADC detector: strongest low-pass, y += (x - y) / 2^n (default 3), used
//               at low speed; it lightens with speed
//   YQ<mV>      comparator threshold in mV (default 1650 = VR_BIAS)
//   YC          set the threshold to the measured VR_IN level (coil connected, motor off)
//   YH<0..7>    comparator hysteresis, n * 10 mV
//   YF<0..15>   comparator: TIM2 input filter (default 15, about 6 us; 0 = off)
//   YL<0..90>   comparator: edge lockout in % of the last pulse period (default 50)
//   Y           print the Y settings
//   K0 / K1     stall guard: stop when the VR speed is far below the commanded speed
//
// Closed loop (vr_track.h: rotor angle from B's pulses and the magnets' signature):
//   CL<revs>    learn, at a steady open-loop speed of at least 200 rpm: the magnets'
//               signature, their angles and the electrical offset (default 10 revolutions)
//   C1 / C0     close the loop (needs a learned, locked tracker and the rotor in step) /
//               back to open loop at the current speed and voltage
//   CT<deg>     angle trim, electrical degrees (closed loop: find the least current)
//   CD<us>      actuation lead, us (default 40: the PWM applies a new vector later)
//   CP<V/rpm>   speed regulator, proportional (default 0.03)
//   CI<V/rpm/s> speed regulator, integral (default 0.02)
//   C           print the closed-loop state
//   In closed loop the voltage is applied 90 degrees ahead of the rotor (q axis); the
//   speed regulator sets its size, 0..Vcap (no braking: D1 cannot return energy), and
//   I<amps> becomes a current limit.
//   W<us>       VR scope: capture 4000 evenly spaced samples <us> apart (default 5, min 2)
//               of VR_IN, I_B and the PWM pins, and print them ("vr ib pwm" per line)
//               between "scope begin ..." and "scope end" (see vr_scope.h). Works while
//               running.
//
// Starting always aligns the rotor first: the field is held at electrical
// angle 0 for L ms so every start begins from a known rotor position.
//
// Safety: software trips on phase / bus overcurrent, DRV8313 nFAULT and low
// VM. A trip disables the driver and prints the reason; send E1 to retry.

#include <Arduino.h>
#include <SimpleFOC.h>
#include "vr_capture.h"
#include "vr_scope.h"
#include "vr_adc.h"
#include "vr_track.h"
#include "fast_adc.h"

// Set by fw_rev.py (git describe --dirty, build time); fallbacks for other build setups.
#ifndef FW_REV
#define FW_REV "unknown"
#endif
#ifndef FW_BUILT
#define FW_BUILT "unknown"
#endif

// ---- Pins (hdd-driver/README.md, "Electronics") ----------------------------
static constexpr int PIN_IN1 = PA8, PIN_IN2 = PA9, PIN_IN3 = PA10;  // TIM1 CH1-3
static constexpr int PIN_EN = PB12, PIN_NFAULT = PB13, PIN_NSLEEP = PB14, PIN_NRESET = PB15;
static constexpr int PIN_VM = PA0;    // VM / 11
static constexpr int PIN_VR = PA1;    // VR pickup, biased at 1.65 V
static constexpr int PIN_IA = PA2;    // INA240A1, 1.65 V +/- 0.4 V/A
static constexpr int PIN_IBUS = PA3;  // INA181A2, 1 V/A
static constexpr int PIN_IB = PA4;    // INA240A1, 1.65 V +/- 0.4 V/A

// ---- Scales ------------------------------------------------------------------
static constexpr float ADC_VREF = 3.3f;
static constexpr float ADC_MAX = 4095.0f;
static constexpr float VM_DIV = 11.0f;
static constexpr float PHASE_V_PER_A = 0.4f;  // 20 mohm * 20 V/V
static constexpr float BUS_V_PER_A = 1.0f;    // 20 mohm * 50 V/V

// ---- Limits / defaults ------------------------------------------------------
#ifndef PWM_HZ
#define PWM_HZ 25000  // DRV8313 allows up to 250 kHz
#endif
// Measured 2026-11-15 with the VR coil: with 6 the disc ran 1.5x the commanded speed
// (B counted 450 pulses/s at R300); with 4 it matches.
static constexpr float POLE_PAIRS = 4;
static constexpr float MAX_VOLTAGE = 6.0f;      // hard cap for V command (also limited to VM / 2)
static constexpr float DEFAULT_VOLTAGE = 1.0f;  // start gently; raise with V
static constexpr float DEFAULT_ACCEL_RPM_S = 30;
static constexpr float ACCEL_BREAK_RPM = 60;
static constexpr float PHASE_TRIP_A = 2.5f;     // DRV8313 OCP is 3 A min
static constexpr float BUS_TRIP_A = 2.5f;       // filtered
static constexpr float VM_MIN = 8.5f;           // DRV8313 UVLO is about 8 V
static constexpr float VM_MAX = 30.0f;
static constexpr uint32_t ALIGN_MS = 600;       // rotor alignment hold
static constexpr float VR_PULSES_PER_REV = 60;  // README: 60 pulses/rev
static constexpr float VR_THRESHOLD_MV = 1650;  // VR_BIAS
static constexpr int VR_HYST = 4;               // 40 mV
static constexpr uint32_t STALL_GRACE_MS = 1500;  // after the ramp ends
static constexpr uint32_t CONTROL_HZ = 20000;     // field-angle update rate (timer interrupt)
static constexpr float R_PHASE_EST = 1.8f;        // start value for the current regulator
static constexpr float I_REG_KI = 20.0f;          // V per A per s
static constexpr float I_REG_MIN_V = 0.05f;
static constexpr uint32_t SAT_MS = 1500;          // regulator pinned at the cap this long -> stop
static constexpr float CL_MIN_RPM = 200;          // closed loop: learn / close only above this
static constexpr float CL_I_LIMIT_KI = 5.0f;      // V per A per s: backs off the voltage above I
static constexpr uint32_t CL_LOST_MS = 300;       // B stale or slow this long -> stop

// ---- Reboot into the ROM bootloader ------------------------------------------
// B stores a magic word in a no-init RAM cell and resets. initVariant() runs
// early in main() on the next boot, before setup(), and jumps to system memory.
static constexpr uint32_t DFU_MAGIC = 0xB007DF00;
static volatile uint32_t dfu_request __attribute__((section(".noinit")));
static constexpr uint32_t SYSTEM_MEMORY = 0x1FFF0000;  // STM32G47x system memory

extern "C" void initVariant() {
  if (dfu_request != DFU_MAGIC) return;
  dfu_request = 0;
  HAL_RCC_DeInit();
  HAL_DeInit();
  SysTick->CTRL = SysTick->LOAD = SysTick->VAL = 0;
  for (int i = 0; i < 8; i++) { NVIC->ICER[i] = 0xFFFFFFFF; NVIC->ICPR[i] = 0xFFFFFFFF; }
  __HAL_RCC_SYSCFG_CLK_ENABLE();
  __HAL_SYSCFG_REMAPMEMORY_SYSTEMFLASH();
  uint32_t sp = *(volatile uint32_t*)SYSTEM_MEMORY;
  uint32_t pc = *(volatile uint32_t*)(SYSTEM_MEMORY + 4);
  __set_MSP(sp);
  ((void (*)(void))pc)();
  while (1) {}
}

BLDCMotor motor(POLE_PAIRS);
BLDCDriver3PWM driver(PIN_IN1, PIN_IN2, PIN_IN3, PIN_EN);
Commander command(Serial);

// Shared with the control interrupt.
static volatile bool running = false, aligning = false;
static volatile float target_rpm = 0, accel_rpm_s = DEFAULT_ACCEL_RPM_S, accel_hi_rpm_s = 0, ramp_rpm = 0;
static volatile uint32_t last_ramp_us = 0, align_start = 0, align_ms = ALIGN_MS;
static volatile uint32_t isr_n = 0, isr_max_cyc = 0, field_revs = 0;
// Open loop: the field's mechanical angle, integrated here (SimpleFOC's own open loop
// keeps a private timestamp, which would jump after a stretch in closed loop).
static volatile float field_mech = 0;
// The electrical angle last applied, in either mode: the Park transform of the currents.
static volatile float el_angle = 0;
// Closed loop
static volatile bool closed_loop = false;
static volatile float uq_cmd = 0;
// Speed regulator: about 30 rpm/s per volt at 600 rpm (measured), so 0.03 V/rpm gives a
// time constant of about 1 s (0.005 swung slowly, +-2 % over several seconds).
static float spd_kp = 0.03f, spd_ki = 0.02f, uq_int = 0;
static uint32_t last_spd_ms = 0, cl_bad_since = 0;
static bool stall_guard = false;
static uint32_t run_id = 0;  // counts E1 starts, so runs can be referred to by number
static uint32_t telemetry_ms = 500, last_telemetry = 0;
static float v_cap = DEFAULT_VOLTAGE, i_set = 0, i_boost = 0, v_cur = 0;  // current regulator
static uint32_t sat_since = 0, last_reg_ms = 0, last_vm_ms = 0;
static float vm_min = 99;
static float reg_iq_sum = 0; static uint32_t reg_n = 0;
static float ia_off = 1.65f, ib_off = 1.65f;  // zero-current voltage, calibrated at boot
static uint32_t steady_since = 0, last_vr_ms = 0;
static float vr_pulses_per_rev = VR_PULSES_PER_REV, vr_hz = 0, vr_rpm = 0;
static float vr_hz_adc = 0, vr_hz_cmp = 0;
static bool vr_use_adc = true;  // YS: which detector feeds vr_hz / vr_rpm
// Window statistics of the currents in the rotor frame (Clarke + Park at the
// open-loop field angle). With the voltage on the q axis, Iq is the torque
// current and Id the part along the rotor axis; at standstill Iq = Uq / R_phase.
struct CurStats {
  uint32_t n = 0;
  float id = 0, iq = 0, iq2 = 0;
  void reset() { *this = CurStats(); }
} cs;
static float ibus_f = 0, ibus_off = 0, ia_peak = 0, ib_peak = 0;

static float volts(int pin) {
  int ch = pin == PIN_VM ? 1 : pin == PIN_VR ? 2 : pin == PIN_IA ? 3 : pin == PIN_IBUS ? 4 : 0;
  uint16_t v = ch ? fast_adc::read1(ch) : 0;
  if (pin == PIN_IB) { uint16_t a; fast_adc::readPair(3, a, v); }
  return v * ADC_VREF / ADC_MAX;
}
static float avgVolts(int pin, int n = 32) {
  float s = 0;
  for (int i = 0; i < n; i++) s += volts(pin);
  return s / n;
}
static float readVM() { return avgVolts(PIN_VM, 64) * VM_DIV; }
static float rpmToRad(float rpm) { return rpm * _2PI / 60.0f; }

static void stopMotor(const char* why) {
  running = false;  // the control interrupt stops moving the field
  aligning = false;
  closed_loop = false;
  noInterrupts();
  motor.disable();
  interrupts();
  ramp_rpm = 0;
  target_rpm = 0;
  Serial.print("DISABLED: ");
  Serial.print(why);
  Serial.print(" (vmmin="); Serial.print(vm_min, 2); Serial.println(")");
}

static bool startMotor() {
  if (digitalRead(PIN_NFAULT) == LOW) { Serial.println("refused: nFAULT is low"); return false; }
  float vm = readVM();
  if (vm < VM_MIN || vm > VM_MAX) {
    Serial.print("refused: VM = "); Serial.print(vm, 2); Serial.println(" V is out of range");
    return false;
  }
  driver.voltage_power_supply = vm;  // PWM scaling follows the real rail
  float cap = min(v_cap, vm * 0.5f);
  v_cur = i_set > 0 ? min(0.5f, cap) : cap;  // soft start: the regulator integrates up from here
  vm_min = 99;
  motor.voltage_limit = v_cur;
  sat_since = 0;
  reg_iq_sum = 0; reg_n = 0; last_reg_ms = millis();
  ramp_rpm = 0;
  field_mech = 0;  // open-loop angle restarts at 0 = where we align
  closed_loop = false;
  uq_int = 0;
  motor.enable();
  steady_since = 0;
  align_start = millis();
  last_ramp_us = micros();
  aligning = align_ms > 0;
  running = true;  // last: starts the control interrupt
  run_id++;
  Serial.print("enabled, run "); Serial.print(run_id);
  Serial.print(" (I="); Serial.print(i_set, 2); Serial.print(" J="); Serial.print(i_boost, 2); Serial.print(" Vcap="); Serial.print(v_cap, 1);
  Serial.print(" A="); Serial.print(accel_rpm_s, 0); Serial.print(" F="); Serial.print(accel_hi_rpm_s, 0);
  Serial.print(" R="); Serial.print(target_rpm, 0); Serial.println(")");
  return true;
}

static void printStatus() {
  float ia = (ia_off - volts(PIN_IA)) / PHASE_V_PER_A;  // sign unverified, only |I| is used
  float ib = (volts(PIN_IB) - ib_off) / PHASE_V_PER_A;
  Serial.print(!running ? "OFF" : aligning ? "ALIGN" : "RUN");
  Serial.print(" vm="); Serial.print(readVM(), 2);
  Serial.print(" rpm="); Serial.print(ramp_rpm, 1);
  Serial.print("/"); Serial.print(target_rpm, 1);
  Serial.print(" Vlim="); Serial.print(motor.voltage_limit, 2);
  Serial.print(" vmmin="); Serial.print(vm_min, 2);
  Serial.print(" cap="); Serial.print(v_cap, 1);
  Serial.print(" Iset="); Serial.print(i_set, 2);
  Serial.print(" pp="); Serial.print(motor.pole_pairs);
  Serial.print(" ibus="); Serial.print(ibus_f, 3);
  Serial.print(" ia="); Serial.print(ia, 3);
  Serial.print(" ib="); Serial.print(ib, 3);
  if (cs.n) {
    float idm = cs.id / cs.n, iqm = cs.iq / cs.n;
    float iqs = sqrtf(max(0.0f, cs.iq2 / cs.n - iqm * iqm));
    Serial.print(" idm="); Serial.print(idm, 3);
    Serial.print(" iqm="); Serial.print(iqm, 3);
    Serial.print(" iqs="); Serial.print(iqs, 3);
    if (iqm > 0.05f) { Serial.print(" rph="); Serial.print(motor.voltage_limit / iqm, 3); }
    Serial.print(" n="); Serial.print(cs.n);
  }
  cs.reset();
  Serial.print(" |ia|pk="); Serial.print(ia_peak, 2);
  Serial.print(" |ib|pk="); Serial.print(ib_peak, 2);
  Serial.print(" vr="); Serial.print(volts(PIN_VR), 3);
  Serial.print(" vrpm="); Serial.print(vr_rpm, 1);
  Serial.print(" vpps="); Serial.print(vr_hz, 1);
  Serial.print(" src="); Serial.print(vr_use_adc ? "adc" : "cmp");
  Serial.print(" apps="); Serial.print(vr_hz_adc, 1);
  Serial.print(" apulses="); Serial.print(vr_adc::pulseCount());
  Serial.print(" app_mv="); Serial.print(vr_adc::ppMv(), 1);
  Serial.print(" alp="); Serial.print(1 << vr_adc::lowPassShift());
  Serial.print(" alevel_mv="); Serial.print(vr_adc::levelMv(), 1);
  { static uint32_t last_s = 0, last_ms = 0; uint32_t s = vr_adc::sampleCount(), ms = millis();
    Serial.print(" adc_hz="); Serial.print(ms > last_ms ? (s - last_s) * 1000.0f / (ms - last_ms) : 0, 0);
    last_s = s; last_ms = ms; }
  Serial.print(" adc_fs="); Serial.print(vr_adc::sampleHz(), 1);
  Serial.print(" aovr="); Serial.print(vr_adc::overruns());
  Serial.print(" mode="); Serial.print(closed_loop ? "CL" : "OL");
  Serial.print(" uq="); Serial.print(uq_cmd, 2);
  Serial.print(" trk_rpm="); Serial.print(vr_track::speedRpm(), 1);
  Serial.print(" lrn="); Serial.print(vr_track::learning() ? 2 : vr_track::learned() ? 1 : 0);
  Serial.print(" lbl="); Serial.print(vr_track::label());
  Serial.print(" shift="); Serial.print(vr_track::lastShift());
  Serial.print(" marg="); Serial.print(vr_track::lastMargin(), 2);
  Serial.print(" corr="); Serial.print(vr_track::corrections());
  Serial.print(" lag="); Serial.print(vr_track::fieldLagDeg(vr_adc::nowT256()), 1);
  Serial.print(" cpps="); Serial.print(vr_hz_cmp, 1);
  Serial.print(" edges="); Serial.print(vr::edgeCount());
  Serial.print(" rej="); Serial.print(vr::rejectedCount());
  Serial.print(" cmp="); Serial.print(vr::comparatorHigh());
  Serial.print(" thr="); Serial.print(vr::threshold(), 0);
  Serial.print(" filt_us="); Serial.print(vr::filterMicros(), 2);
  Serial.print(" lock="); Serial.print(vr::lockout());
  Serial.print(" pwm_hz=");
  Serial.print((float)HAL_RCC_GetPCLK2Freq() * ((RCC->CFGR & RCC_CFGR_PPRE2) >= RCC_CFGR_PPRE2_2 ? 2 : 1) /
               (((TIM1->CR1 & TIM_CR1_CMS) ? 2.0f : 1.0f) * (TIM1->ARR + 1) * (TIM1->PSC + 1)), 0);
  { static uint32_t last_n = 0, last_ms = 0, last_revs = 0; uint32_t n = isr_n, ms = millis(), rv = field_revs;
    Serial.print(" fieldrpm="); Serial.print(ms > last_ms ? (rv - last_revs) * 60000.0f / (ms - last_ms) : 0, 1);
    last_revs = rv;
    Serial.print(" isr_hz="); Serial.print(ms > last_ms ? (n - last_n) * 1000.0f / (ms - last_ms) : 0, 0);
    Serial.print(" isr_us="); Serial.print(isr_max_cyc / (SystemCoreClock / 1e6f), 1);
    last_n = n; last_ms = ms; isr_max_cyc = 0; }
  Serial.print(" nFT="); Serial.print(digitalRead(PIN_NFAULT));
  Serial.print(" fw="); Serial.println(FW_REV);
  ia_peak = ib_peak = 0;
}

static void cmdEnable(char* c) {
  if (atoi(c)) startMotor(); else stopMotor("by command");
}
static void cmdRpm(char* c) { target_rpm = atof(c); Serial.print("target rpm "); Serial.println(target_rpm); }
static void cmdAccel(char* c) { accel_rpm_s = max(1.0f, fabsf((float)atof(c))); }
static void cmdAccelHi(char* c) { accel_hi_rpm_s = max(0.0f, fabsf((float)atof(c))); }
static void cmdVolt(char* c) {
  v_cap = constrain((float)atof(c), 0.0f, MAX_VOLTAGE);
  if (i_set <= 0) motor.voltage_limit = v_cap;
  Serial.print("Vcap "); Serial.println(v_cap, 2);
}
static void cmdBoost(char* c) { i_boost = constrain((float)atof(c), 0.0f, 2.0f); Serial.print("Jboost "); Serial.println(i_boost, 2); }
static void cmdCurrent(char* c) {
  i_set = constrain((float)atof(c), 0.0f, 1.5f);
  if (i_set <= 0) motor.voltage_limit = v_cap;
  Serial.print("Iset "); Serial.println(i_set, 2);
}
static void cmdPoles(char* c) {
  int n = atoi(c);
  if (n >= 1 && n <= 32) motor.pole_pairs = n, vr_track::setPolePairs(n);
}
static void cmdTelemetry(char* c) { telemetry_ms = max(0, atoi(c)); }
static void cmdStatus(char*) { printStatus(); }
// Histogram of raw phase-current samples, in 20 mV bins around the offset.
// Blocks the loop for ~100 ms; PWM keeps the last duty, so use it in a hold.
static void cmdDiag(char*) {
  static uint16_t ha[64], hb[64];
  memset(ha, 0, sizeof ha); memset(hb, 0, sizeof hb);
  const int N = 3000;
  uint32_t t0 = micros();
  for (int i = 0; i < N; i++) {
    uint16_t ra, rb;
    fast_adc::readPair(3, ra, rb);
    // bin = (V - offset) / 20 mV, centered at 32
    int ba = 32 + (int)floorf(((ra * ADC_VREF / ADC_MAX) - ia_off) / 0.02f);
    int bb = 32 + (int)floorf(((rb * ADC_VREF / ADC_MAX) - ib_off) / 0.02f);
    ha[constrain(ba, 0, 63)]++; hb[constrain(bb, 0, 63)]++;
  }
  Serial.print("diag: "); Serial.print(N); Serial.print(" samples, ");
  Serial.print((micros() - t0) / (2.0f * N), 2); Serial.println(" us per read");
  for (int ch = 0; ch < 2; ch++) {
    Serial.print(ch ? "ib " : "ia ");
    Serial.println("(bin = 20 mV from the zero-current offset; count)");
    uint16_t* h = ch ? hb : ha;
    for (int i = 0; i < 64; i++) if (h[i]) { Serial.print(i - 32); Serial.print(":"); Serial.print(h[i]); Serial.print(" "); }
    Serial.println();
  }
}
static void cmdBootloader(char*) {
  motor.disable();
  Serial.println("rebooting into DFU bootloader");
  Serial.flush();
  delay(50);
  dfu_request = DFU_MAGIC;
  NVIC_SystemReset();
}
static void cmdAlign(char* c) { align_ms = constrain(atoi(c), 0, 5000); }
static void cmdStall(char* c) { stall_guard = atoi(c) != 0; }
static void calibrateThreshold() {
  if (running) { Serial.println("refused: stop the motor first"); return; }
  float mv = avgVolts(PIN_VR, 256) * 1000.0f;
  vr::setThreshold(mv);
  Serial.print("threshold = "); Serial.print(mv, 0); Serial.println(" mV");
}
// One command letter for the VR detector settings: the Commander has only 20 slots.
static void cmdVrSettings(char* c) {
  const char sub = (c && *c) ? (char)toupper(*c) : 0;
  const char* arg = (c && *c) ? c + 1 : "";
  if (sub == 'N') { float n = atof(arg); if (n >= 1 && n <= 1000) vr_pulses_per_rev = n; }
  else if (sub == 'Q') vr::setThreshold(atof(arg));
  else if (sub == 'H') vr::setHysteresis(atoi(arg));
  else if (sub == 'C') { calibrateThreshold(); return; }
  else if (sub == 'F') vr::setFilter(atoi(arg));
  else if (sub == 'L') vr::setLockout(atoi(arg));
  else if (sub == 'S') vr_use_adc = atoi(arg) != 0;
  else if (sub == 'P') vr_adc::setHystPercent(atoi(arg));
  else if (sub == 'M') vr_adc::setFloorMv((float)atof(arg));
  else if (sub == 'A') vr_adc::setLowPassMaxShift(atoi(arg));
  Serial.print("VR source "); Serial.print(vr_use_adc ? "adc" : "cmp");
  Serial.print("; adc hyst "); Serial.print(vr_adc::hystPercent());
  Serial.print(" %, floor "); Serial.print(vr_adc::floorMv(), 1);
  Serial.print(" mV, low-pass up to 1/"); Serial.print(1 << vr_adc::lowPassMaxShift());
  Serial.print("; pulses/rev "); Serial.print(vr_pulses_per_rev, 0);
  Serial.print("; cmp threshold "); Serial.print(vr::threshold(), 0);
  Serial.print(" mV, hyst "); Serial.print(vr::hysteresis() * 10);
  Serial.print(" mV, filter "); Serial.print(vr::filter());
  Serial.print(" = "); Serial.print(vr::filterMicros(), 2); Serial.print(" us, lockout ");
  Serial.print(vr::lockout()); Serial.println(" %");
}
static void cmdScope(char* c) {
  float us = (c && *c) ? (float)atof(c) : 5.0f;
  vr_scope::Result r = vr_scope::capture(us);
  Serial.print("scope begin n="); Serial.print(r.n);
  Serial.print(" interval_us="); Serial.print(r.interval_us, 4);
  Serial.print(" edges="); Serial.print(r.edges);
  Serial.print(" state="); Serial.print(!running ? "OFF" : aligning ? "ALIGN" : "RUN");
  Serial.print(" rpm="); Serial.print(ramp_rpm, 1);
  Serial.print(" pp="); Serial.print(motor.pole_pairs);
  Serial.print(" Vlim="); Serial.print(motor.voltage_limit, 2);
  Serial.print(" thr="); Serial.print(vr::threshold(), 0);
  Serial.print(" hyst="); Serial.print(vr::hysteresis());
  Serial.print(" ib_off="); Serial.print(ib_off, 4);
  Serial.print(" vrpm="); Serial.println(vr_rpm, 1);
  vr_scope::print(Serial);
  Serial.println("scope end");
}
static void printClosedLoop() {
  Serial.print("closed loop: mode "); Serial.print(closed_loop ? "CL" : "OL");
  Serial.print(", tracker "); Serial.print(vr_track::learning() ? "learning" : vr_track::learned() ? "learned" : "not learned");
  Serial.print(vr_track::locked() ? ", locked" : ", not locked");
  Serial.print(" (shift "); Serial.print(vr_track::lastShift());
  Serial.print(", margin "); Serial.print(vr_track::lastMargin(), 2);
  Serial.print(", corrections "); Serial.print(vr_track::corrections());
  Serial.print("), offset "); Serial.print(vr_track::offsetDeg(), 1);
  Serial.print(" deg (spread "); Serial.print(vr_track::offsetSpreadDeg(), 1);
  Serial.print("), trim "); Serial.print(vr_track::trimDeg(), 1);
  Serial.print(" deg, lead "); Serial.print(vr_track::leadUs(), 0);
  Serial.print(" us, speed "); Serial.print(vr_track::speedRpm(), 1);
  Serial.print(" rpm, uq "); Serial.print(uq_cmd, 2);
  Serial.print(" V, PI "); Serial.print(spd_kp, 4); Serial.print(" / "); Serial.println(spd_ki, 4);
}
// The closed-loop commands under one letter (the Commander has only 20 slots).
static void cmdClosed(char* c) {
  const char sub = (c && *c) ? (char)toupper(*c) : 0;
  const char* arg = (c && *c) ? c + 1 : "";
  const float meas = vr_track::speedRpm();
  if (sub == 'L') {
    if (!running || aligning || closed_loop) { Serial.println("refused: learn while running in open loop"); return; }
    if (fabsf(ramp_rpm - target_rpm) > 0.01f || ramp_rpm < CL_MIN_RPM) { Serial.println("refused: learn at a steady speed of at least 200 rpm"); return; }
    if (fabsf(meas - ramp_rpm) > 0.05f * ramp_rpm) { Serial.println("refused: the rotor is not in step (B speed differs)"); return; }
    const int revs = *arg ? atoi(arg) : 10;
    Serial.println(vr_track::startLearning(revs) ? "learning" : "refused: already learning");
    return;
  }
  if (sub == '1') {
    if (!running || aligning || closed_loop) { Serial.println("refused: close the loop while running in open loop"); return; }
    if (!vr_track::learned() || !vr_track::locked()) { Serial.println("refused: the tracker is not learned and locked (CL, then wait a few revolutions)"); return; }
    if (ramp_rpm < CL_MIN_RPM || fabsf(meas - ramp_rpm) > 0.05f * ramp_rpm) { Serial.println("refused: the rotor is not in step above 200 rpm"); return; }
    // Closed loop needs far less voltage than open loop (0.3-0.9 V against 2.1-2.5 V at
    // 600 rpm): starting from the open-loop voltage overshot to +12 %.
    uq_int = 0.3f * motor.voltage_limit;
    uq_cmd = uq_int;
    reg_iq_sum = 0; reg_n = 0;
    last_spd_ms = millis();
    cl_bad_since = 0;
    closed_loop = true;
    Serial.println("closed loop on");
    return;
  }
  if (sub == '0') {
    if (!closed_loop) { Serial.println("already open loop"); return; }
    noInterrupts();
    // Carry on from the angle and voltage just applied.
    field_mech = el_angle / motor.pole_pairs;
    v_cur = uq_cmd;
    motor.voltage_limit = uq_cmd;
    closed_loop = false;
    interrupts();
    reg_iq_sum = 0; reg_n = 0; sat_since = 0; last_reg_ms = millis();
    Serial.println("open loop");
    return;
  }
  if (sub == 'T') vr_track::setTrimDeg(atof(arg));
  else if (sub == 'D') vr_track::setLeadUs(atof(arg));
  else if (sub == 'P') spd_kp = constrain((float)atof(arg), 0.0f, 0.1f);
  else if (sub == 'I') spd_ki = constrain((float)atof(arg), 0.0f, 1.0f);
  printClosedLoop();
}

static HardwareTimer* control_timer = nullptr;
static void controlStep2();

// Runs at CONTROL_HZ in an interrupt: holds the field at angle 0 during the
// alignment, then ramps the speed and advances the open-loop field, or in closed loop
// applies the voltage at the rotor angle from B. B's samples are processed here too.
static void controlStep() {
  uint32_t t0 = DWT->CYCCNT;
  isr_n = isr_n + 1;
  static float last_angle = 0;
  controlStep2();
  if (running && !closed_loop) {
    float a = field_mech;
    if (a < last_angle - 3.0f) field_revs = field_revs + 1;  // wrapped past 2*pi
    last_angle = a;
  }
  uint32_t d = DWT->CYCCNT - t0;
  if (d > isr_max_cyc) isr_max_cyc = d;
}
// The speed ramp (A below ACCEL_BREAK_RPM, F above); returns dt in s.
static float rampStep() {
  uint32_t now = micros();
  float dt = (now - last_ramp_us) * 1e-6f;
  last_ramp_us = now;
  float r = ramp_rpm;
  float acc = (fabsf(r) >= ACCEL_BREAK_RPM && accel_hi_rpm_s > 0) ? accel_hi_rpm_s : accel_rpm_s;
  float step = acc * dt;
  r += constrain(target_rpm - r, -step, step);
  ramp_rpm = r;
  return dt;
}
static void controlStep2() {
  const bool run = running;
  if (run && !closed_loop) {
    // Open loop: the field at field_mech, the voltage motor.voltage_limit (as SimpleFOC's
    // velocity_openloop does, with our own angle and timing).
    float w = 0;
    if (aligning) {
      field_mech = 0;
      if (millis() - align_start >= align_ms) {
        aligning = false;
        last_ramp_us = micros();
      }
    } else {
      const float dt = rampStep();
      w = rpmToRad(ramp_rpm);
      float a = field_mech + w * dt;
      a = fmodf(a, _2PI);
      field_mech = a < 0 ? a + _2PI : a;
    }
    const float th = field_mech * motor.pole_pairs;
    motor.setPhaseVoltage(motor.voltage_limit, 0, th);
    el_angle = th;
    vr_track::setField(th, w * motor.pole_pairs);
  }
  vr_adc::isrPoll();  // B's new samples; pulses go to vr_track
  if (run && closed_loop) {
    rampStep();
    const float th = vr_track::electricalAngle(vr_adc::nowT256());
    motor.setPhaseVoltage(uq_cmd, 0, th);
    el_angle = th;
  }
}

void setup() {
  Serial.begin(115200);

  // Driver off at reset (EN has pull-downs); wake it from sleep.
  pinMode(PIN_EN, OUTPUT); digitalWrite(PIN_EN, LOW);
  pinMode(PIN_NFAULT, INPUT_PULLUP);
  pinMode(PIN_NSLEEP, OUTPUT); digitalWrite(PIN_NSLEEP, HIGH);
  pinMode(PIN_NRESET, OUTPUT); digitalWrite(PIN_NRESET, HIGH);

  pinMode(PIN_VM, INPUT_ANALOG); pinMode(PIN_VR, INPUT_ANALOG); pinMode(PIN_IA, INPUT_ANALOG);
  pinMode(PIN_IBUS, INPUT_ANALOG); pinMode(PIN_IB, INPUT_ANALOG);
  fast_adc::begin();
  delay(50);
  // Zero-current offsets, driver disabled so no phase current flows.
  ia_off = avgVolts(PIN_IA, 256);
  ib_off = avgVolts(PIN_IB, 256);
  ibus_off = avgVolts(PIN_IBUS, 256) / BUS_V_PER_A;

  driver.voltage_power_supply = 12;  // replaced with the measured VM on E1
  driver.voltage_limit = MAX_VOLTAGE;
  driver.pwm_frequency = PWM_HZ;
  if (!driver.init()) { Serial.println("driver init failed"); }
  motor.linkDriver(&driver);

  motor.controller = MotionControlType::velocity_openloop;
  motor.voltage_limit = DEFAULT_VOLTAGE;
  motor.velocity_limit = rpmToRad(6000);
  motor.init();
  motor.disable();  // init() enables the driver; keep it off until E1

  command.add('E', cmdEnable, "enable 0/1");
  command.add('R', cmdRpm, "target rpm");
  command.add('A', cmdAccel, "accel rpm/s");
  command.add('F', cmdAccelHi, "accel above break rpm/s");
  command.add('V', cmdVolt, "voltage cap");
  command.add('J', cmdBoost, "start boost current A");
  command.add('I', cmdCurrent, "current regulation A");
  command.add('P', cmdPoles, "pole pairs");
  command.add('T', cmdTelemetry, "telemetry ms");
  command.add('S', cmdStatus, "status");
  command.add('D', cmdDiag, "ADC histogram");
  command.add('B', cmdBootloader, "reboot to DFU");
  command.add('L', cmdAlign, "align ms");
  command.add('K', cmdStall, "stall guard 0/1");
  command.add('Y', cmdVrSettings, "VR detectors: YS YP YM YA YN YQ YH YC YF YL");
  command.add('W', cmdScope, "VR scope: W<us between samples>");
  command.add('C', cmdClosed, "closed loop: CL C1 C0 CT CD CP CI");
  // SimpleFOC 2.3.4's Commander has fixed arrays of 20 commands and add() does not
  // check: a 21st overwrites memory (it broke E and R once). 17 are used; fold new
  // ones into an existing letter, as Y and C do.

  // Field-angle update (alignment, ramp, open-loop move) at a fixed rate in an
  // interrupt, independent of how long the main loop takes.
  CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
  DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
  control_timer = new HardwareTimer(TIM3);
  control_timer->setOverflow(CONTROL_HZ, HERTZ_FORMAT);
  control_timer->setInterruptPriority(1, 0);
  control_timer->attachInterrupt(controlStep);
  control_timer->resume();

  vr::begin(VR_THRESHOLD_MV, VR_HYST);
  vr::pulseHz();  // prime the snapshot
  vr_adc::begin();  // needs TIM1 running (driver.init)
  vr_adc::pulseHz();
  vr_track::begin(motor.pole_pairs, vr_adc::sampleHz());

  Serial.print("hdd-driver ready; driver is OFF. fw "); Serial.print(FW_REV);
  Serial.print(" built "); Serial.println(FW_BUILT);
  printStatus();
}

void loop() {
  vr_track::poll();  // finishes learning, checks the lock once per revolution

  // VR speed, every 100 ms.
  if (millis() - last_vr_ms >= 100) {
    last_vr_ms = millis();
    vr_hz_cmp = vr::pulseHz();
    vr_hz_adc = vr_adc::pulseHz();
    vr_hz = vr_use_adc ? vr_hz_adc : vr_hz_cmp;
    vr_rpm = vr_hz * 60.0f / vr_pulses_per_rev;
    // Stall guard: once the ramp has reached the target for a while, the
    // measured speed must be near it. Off by default (needs the coil).
    if (running && !aligning && stall_guard && fabsf(target_rpm) >= 10) {
      if (fabsf(ramp_rpm - target_rpm) > 0.01f) steady_since = 0;
      else if (!steady_since) steady_since = millis();
      if (steady_since && millis() - steady_since > STALL_GRACE_MS &&
          vr_rpm < 0.5f * fabsf(target_rpm))
        stopMotor("stall: VR speed far below the target");
    }
  }

  // Protection and rotor-frame current statistics. One simultaneous ia/ib pair per pass.
  {
    uint16_t ra, rb;
    fast_adc::readPair(3, ra, rb);
    float sa = ra * ADC_VREF / ADC_MAX, sb = rb * ADC_VREF / ADC_MAX;
    float sia = (ia_off - sa) / PHASE_V_PER_A;  // sign convention as in printStatus()
    float sib = (sb - ib_off) / PHASE_V_PER_A;
    float ia = fabsf(sia), ib = fabsf(sib);
    if (running) {
      float ang = el_angle;  // the frame of the voltage just applied (field or rotor)
      float c = cosf(ang), sn = sinf(ang);
      float ialpha = sia, ibeta = (sia + 2.0f * sib) * 0.57735027f;
      float id = ialpha * c + ibeta * sn, iq = -ialpha * sn + ibeta * c;
      cs.n++; cs.id += id; cs.iq += iq; cs.iq2 += iq * iq;
      reg_iq_sum += iq; reg_n++;
    }
    ia_peak = max(ia_peak, ia);
    ib_peak = max(ib_peak, ib);
    ibus_f += 0.01f * ((volts(PIN_IBUS) / BUS_V_PER_A - ibus_off) - ibus_f);
    if (running) {
      if (ia > PHASE_TRIP_A || ib > PHASE_TRIP_A) stopMotor("phase overcurrent");
      else if (ibus_f > BUS_TRIP_A) stopMotor("bus overcurrent");
      else if (digitalRead(PIN_NFAULT) == LOW) stopMotor("DRV8313 nFAULT (OCP/OTP/UVLO)");
    }
  }

  // Lowest supply voltage seen during the run, sampled every ms.
  if (running && millis() != last_vm_ms) {
    last_vm_ms = millis();
    float vm = volts(PIN_VM) * VM_DIV;
    if (vm < vm_min) vm_min = vm;
    if (vm < VM_MIN - 0.5f) stopMotor("VM sagged below the driver's UVLO");
  }

  // Closed loop, every 2 ms: speed regulator on B's speed -> q voltage, I as a current
  // limit, and a stop when B goes stale or the rotor falls well behind the ramp.
  if (running && closed_loop && millis() - last_spd_ms >= 2) {
    const float dt = (millis() - last_spd_ms) * 1e-3f;
    last_spd_ms = millis();
    const float meas = vr_track::speedRpm();
    const float err = ramp_rpm - meas;
    const float cap = min(v_cap, driver.voltage_power_supply * 0.5f);
    uq_int = constrain(uq_int + spd_ki * err * dt, 0.0f, cap);
    if (i_set > 0 && reg_n) {
      const float iq = reg_iq_sum / reg_n;
      if (iq > i_set) uq_int = max(0.0f, uq_int - CL_I_LIMIT_KI * (iq - i_set) * dt);
    }
    reg_iq_sum = 0; reg_n = 0;
    const float uq = constrain(spd_kp * err + uq_int, 0.0f, cap);
    uq_cmd = uq;
    motor.voltage_limit = uq;  // for the status line
    const bool valid = vr_track::angleValid(vr_adc::nowT256());
    if (!valid || meas < 0.7f * ramp_rpm) {
      if (!cl_bad_since) cl_bad_since = millis();
      else if (millis() - cl_bad_since > CL_LOST_MS) stopMotor("closed loop: B stale or rotor far behind the ramp");
    } else cl_bad_since = 0;
  }

  // Current regulator (open loop), every 2 ms: integrate the torque-current error into the voltage.
  if (running && !closed_loop && i_set > 0 && millis() - last_reg_ms >= 2 && reg_n) {
    float dt = (millis() - last_reg_ms) * 1e-3f;
    last_reg_ms = millis();
    float iq = reg_iq_sum / reg_n;
    reg_iq_sum = 0; reg_n = 0;
    float cap = min(v_cap, driver.voltage_power_supply * 0.5f);
    float target = i_set;
    if (i_boost > i_set) {  // taper from i_boost at standstill to i_set at ACCEL_BREAK_RPM
      float f = constrain(fabsf(ramp_rpm) / ACCEL_BREAK_RPM, 0.0f, 1.0f);
      target = i_boost + (i_set - i_boost) * f;
    }
    v_cur = constrain(v_cur + I_REG_KI * (target - iq) * dt, I_REG_MIN_V, cap);
    motor.voltage_limit = v_cur;
    // Pinned at the cap without reaching the current: the rotor cannot be held.
    if (v_cur >= cap - 0.01f && iq < 0.8f * target && !aligning) {
      if (!sat_since) sat_since = millis();
      else if (millis() - sat_since > SAT_MS) stopMotor("voltage cap reached, current not held (lost sync or cap too low)");
    } else sat_since = 0;
  }

  command.run();

  if (telemetry_ms && millis() - last_telemetry >= telemetry_ms) {
    last_telemetry = millis();
    if (running) printStatus();
  }
}
