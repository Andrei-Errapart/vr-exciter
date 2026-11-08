// hdd-driver firmware, bring-up version.
//
// Open-loop velocity control of the HDD spindle motor through the SimpleFOC
// Mini (DRV8313). The driver stays OFF after reset; spin it with the serial
// commands below (USB-C, 115200 8N1, any terminal, newline terminated).
//
//   E1 / E0     enable / disable the driver
//   R<rpm>      target speed in rpm (mechanical), e.g. R300. Negative reverses.
//   A<rpm/s>    acceleration, e.g. A60
//   V<volts>    open-loop phase voltage limit (max MAX_VOLTAGE)
//   P<n>        motor pole pairs (default POLE_PAIRS)
//   T<ms>       telemetry period, 0 = off
//   S           print status
//   D           (diagnostic, during an alignment hold) histogram of raw ia/ib samples
//   B           reboot into the ROM DFU bootloader (for flashing without the BOOT0 button)
//   L<ms>       rotor alignment hold before the ramp (default ALIGN_MS, 0 = skip)
//
// VR pickup (COMP1 + TIM2 capture, see vr_capture.h), reported as vrpm / vpps:
//   N<n>        VR pulses per revolution (default VR_PULSES_PER_REV)
//   Q<mV>       comparator threshold in mV (default 1650 = VR_BIAS)
//   C           set the threshold to the measured VR_IN level (coil connected, motor off)
//   H<0..7>     comparator hysteresis, n * 10 mV
//   K0 / K1     stall guard: stop when the VR speed is far below the commanded speed
//
// Starting always aligns the rotor first: the field is held at electrical
// angle 0 for L ms so every start begins from a known rotor position.
//
// Safety: software trips on phase / bus overcurrent, DRV8313 nFAULT and low
// VM. A trip disables the driver and prints the reason; send E1 to retry.

#include <Arduino.h>
#include <SimpleFOC.h>
#include "vr_capture.h"

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
static constexpr float POLE_PAIRS = 6;          // unverified: typical 12-pole 3.5" spindle
static constexpr float MAX_VOLTAGE = 3.0f;      // hard cap for V command
static constexpr float DEFAULT_VOLTAGE = 1.0f;  // start gently; raise with V
static constexpr float DEFAULT_ACCEL_RPM_S = 30;
static constexpr float PHASE_TRIP_A = 2.5f;     // DRV8313 OCP is 3 A min
static constexpr float BUS_TRIP_A = 2.5f;       // filtered
static constexpr float VM_MIN = 8.5f;           // DRV8313 UVLO is about 8 V
static constexpr float VM_MAX = 30.0f;
static constexpr uint32_t ALIGN_MS = 600;       // rotor alignment hold
static constexpr float VR_PULSES_PER_REV = 60;  // README: 60 pulses/rev
static constexpr float VR_THRESHOLD_MV = 1650;  // VR_BIAS
static constexpr int VR_HYST = 4;               // 40 mV
static constexpr uint32_t STALL_GRACE_MS = 1500;  // after the ramp ends

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

static bool running = false, aligning = false, stall_guard = false;
static float target_rpm = 0, accel_rpm_s = DEFAULT_ACCEL_RPM_S, ramp_rpm = 0;
static uint32_t telemetry_ms = 500, last_telemetry = 0, last_ramp_us = 0;
static float ia_off = 1.65f, ib_off = 1.65f;  // zero-current voltage, calibrated at boot
static uint32_t align_ms = ALIGN_MS, align_start = 0, steady_since = 0, last_vr_ms = 0;
static float vr_pulses_per_rev = VR_PULSES_PER_REV, vr_hz = 0, vr_rpm = 0;
// Window statistics of the currents in the rotor frame (Clarke + Park at the
// open-loop field angle). With the voltage on the q axis, Iq is the torque
// current and Id the part along the rotor axis; at standstill Iq = Uq / R_phase.
struct CurStats {
  uint32_t n = 0;
  float id = 0, iq = 0, iq2 = 0;
  void reset() { *this = CurStats(); }
} cs;
static float ibus_f = 0, ibus_off = 0, ia_peak = 0, ib_peak = 0;

static float volts(int pin) { return analogRead(pin) * ADC_VREF / ADC_MAX; }
static float avgVolts(int pin, int n = 32) {
  float s = 0;
  for (int i = 0; i < n; i++) s += volts(pin);
  return s / n;
}
static float readVM() { return avgVolts(PIN_VM, 16) * VM_DIV; }
static float rpmToRad(float rpm) { return rpm * _2PI / 60.0f; }

static void stopMotor(const char* why) {
  motor.disable();
  running = false;
  aligning = false;
  ramp_rpm = 0;
  target_rpm = 0;
  Serial.print("DISABLED: ");
  Serial.println(why);
}

static bool startMotor() {
  if (digitalRead(PIN_NFAULT) == LOW) { Serial.println("refused: nFAULT is low"); return false; }
  float vm = readVM();
  if (vm < VM_MIN || vm > VM_MAX) {
    Serial.print("refused: VM = "); Serial.print(vm, 2); Serial.println(" V is out of range");
    return false;
  }
  driver.voltage_power_supply = vm;  // PWM scaling follows the real rail
  motor.voltage_limit = min(motor.voltage_limit, vm * 0.5f);
  ramp_rpm = 0;
  motor.shaft_angle = 0;  // open-loop angle restarts at 0 = where we align
  motor.enable();
  running = true;
  steady_since = 0;
  aligning = align_ms > 0;
  align_start = millis();
  last_ramp_us = micros();
  Serial.println(aligning ? "enabled, aligning" : "enabled");
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
  Serial.print(" edges="); Serial.print(vr::edgeCount());
  Serial.print(" cmp="); Serial.print(vr::comparatorHigh());
  Serial.print(" thr="); Serial.print(vr::threshold(), 0);
  Serial.print(" pwm_hz=");
  Serial.print((float)HAL_RCC_GetPCLK2Freq() * ((RCC->CFGR & RCC_CFGR_PPRE2) >= RCC_CFGR_PPRE2_2 ? 2 : 1) /
               (((TIM1->CR1 & TIM_CR1_CMS) ? 2.0f : 1.0f) * (TIM1->ARR + 1) * (TIM1->PSC + 1)), 0);
  Serial.print(" nFT="); Serial.println(digitalRead(PIN_NFAULT));
  ia_peak = ib_peak = 0;
}

static void cmdEnable(char* c) {
  if (atoi(c)) startMotor(); else stopMotor("by command");
}
static void cmdRpm(char* c) { target_rpm = atof(c); Serial.print("target rpm "); Serial.println(target_rpm); }
static void cmdAccel(char* c) { accel_rpm_s = max(1.0f, fabsf((float)atof(c))); }
static void cmdVolt(char* c) {
  float v = constrain((float)atof(c), 0.0f, MAX_VOLTAGE);
  motor.voltage_limit = v;
  Serial.print("Vlim "); Serial.println(v, 2);
}
static void cmdPoles(char* c) {
  int n = atoi(c);
  if (n >= 1 && n <= 32) motor.pole_pairs = n;
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
    int ra = analogRead(PIN_IA), rb = analogRead(PIN_IB);
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
static void cmdPulses(char* c) { float n = atof(c); if (n >= 1 && n <= 1000) vr_pulses_per_rev = n; }
static void cmdThreshold(char* c) { vr::setThreshold(atof(c)); }
static void cmdHyst(char* c) { vr::setHysteresis(atoi(c)); }
static void cmdStall(char* c) { stall_guard = atoi(c) != 0; }
static void cmdCalibrate(char*) {
  if (running) { Serial.println("refused: stop the motor first"); return; }
  float mv = avgVolts(PIN_VR, 256) * 1000.0f;
  vr::setThreshold(mv);
  Serial.print("threshold = "); Serial.print(mv, 0); Serial.println(" mV");
}

void setup() {
  Serial.begin(115200);

  // Driver off at reset (EN has pull-downs); wake it from sleep.
  pinMode(PIN_EN, OUTPUT); digitalWrite(PIN_EN, LOW);
  pinMode(PIN_NFAULT, INPUT_PULLUP);
  pinMode(PIN_NSLEEP, OUTPUT); digitalWrite(PIN_NSLEEP, HIGH);
  pinMode(PIN_NRESET, OUTPUT); digitalWrite(PIN_NRESET, HIGH);

  analogReadResolution(12);
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
  command.add('V', cmdVolt, "voltage limit");
  command.add('P', cmdPoles, "pole pairs");
  command.add('T', cmdTelemetry, "telemetry ms");
  command.add('S', cmdStatus, "status");
  command.add('D', cmdDiag, "ADC histogram");
  command.add('B', cmdBootloader, "reboot to DFU");
  command.add('L', cmdAlign, "align ms");
  command.add('N', cmdPulses, "VR pulses/rev");
  command.add('Q', cmdThreshold, "VR threshold mV");
  command.add('H', cmdHyst, "VR hysteresis 0..7");
  command.add('C', cmdCalibrate, "VR threshold = measured");
  command.add('K', cmdStall, "stall guard 0/1");

  vr::begin(VR_THRESHOLD_MV, VR_HYST);
  vr::pulseHz();  // prime the snapshot

  Serial.println("hdd-driver ready; driver is OFF. Commands: E1 R<rpm> A V P T S");
  printStatus();
}

void loop() {
  // Open-loop speed with a software ramp (the platters have inertia).
  if (running && aligning) {
    motor.move(0);  // field fixed at electrical angle 0
    if (millis() - align_start >= align_ms) {
      aligning = false;
      last_ramp_us = micros();
    }
  } else if (running) {
    uint32_t now = micros();
    float dt = (now - last_ramp_us) * 1e-6f;
    last_ramp_us = now;
    float step = accel_rpm_s * dt;
    ramp_rpm += constrain(target_rpm - ramp_rpm, -step, step);
    motor.move(rpmToRad(ramp_rpm));
  }

  // VR speed, every 100 ms.
  if (millis() - last_vr_ms >= 100) {
    last_vr_ms = millis();
    vr_hz = vr::pulseHz();
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

  // Protection.
  float ia = fabsf(volts(PIN_IA) - ia_off) / PHASE_V_PER_A;
  float ib = fabsf(volts(PIN_IB) - ib_off) / PHASE_V_PER_A;
  if (running) {
    // Signed phase currents, same convention as printStatus().
    float sia = (ia_off - volts(PIN_IA)) / PHASE_V_PER_A;
    float sib = (volts(PIN_IB) - ib_off) / PHASE_V_PER_A;
    float ang = motor.shaft_angle * motor.pole_pairs;
    float c = cosf(ang), sn = sinf(ang);
    float ialpha = sia, ibeta = (sia + 2.0f * sib) * 0.57735027f;
    float id = ialpha * c + ibeta * sn, iq = -ialpha * sn + ibeta * c;
    cs.n++; cs.id += id; cs.iq += iq; cs.iq2 += iq * iq;
  }
  ia_peak = max(ia_peak, ia);
  ib_peak = max(ib_peak, ib);
  ibus_f += 0.01f * ((volts(PIN_IBUS) / BUS_V_PER_A - ibus_off) - ibus_f);
  if (running) {
    if (ia > PHASE_TRIP_A || ib > PHASE_TRIP_A) stopMotor("phase overcurrent");
    else if (ibus_f > BUS_TRIP_A) stopMotor("bus overcurrent");
    else if (digitalRead(PIN_NFAULT) == LOW) stopMotor("DRV8313 nFAULT (OCP/OTP/UVLO)");
  }

  command.run();

  if (telemetry_ms && millis() - last_telemetry >= telemetry_ms) {
    last_telemetry = millis();
    if (running) printStatus();
  }
}
