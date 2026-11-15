// VR pickup coil -> speed measurement.
//
// VR_IN (PA1) goes to COMP1's non-inverting input. The threshold is DAC3 CH1,
// an on-chip DAC with no pin, on COMP1's inverting input. COMP1's output feeds
// TIM2 input capture 1 (TI1SEL = comp1_out), so no pin or EXTI is needed. The
// 32-bit TIM2 timestamps every rising edge.
//
// While the motor is driven, the PWM switching puts short spikes on VR_IN that the
// comparator follows (scope bursts, 2026-11-15: thousands of false edges/s, little
// visible to the ADC). Two stages reject them:
//   - TIM2's input filter: the comparator output must hold for N samples before
//     TIM2 sees the change (default IC1F = 15: 8 samples at f_tim/128, about 6 us).
//     A real VR half-period is at least 166 us even at 3000 rpm (60 pulses/rev).
//   - Lockout: an edge sooner than lockout% of the shorter of the last two accepted
//     periods (and never sooner than LOCKOUT_MIN_US) after the last accepted edge is
//     rejected. The shorter of two keeps one missed pulse (a 2T period) from locking
//     out the next real one. After a pause the first edge starts fresh, so a stopped
//     disc is no trap.
#pragma once
#include <Arduino.h>

namespace vr {

constexpr float LOCKOUT_MIN_US = 100.0f;  // limits the count to 10 kHz (10000 rpm)

// Call once. Threshold in mV is the comparator trip level (the coil is biased
// at 1.65 V, so about 1650); hyst 0..7 = 0..70 mV in 10 mV steps.
void begin(float threshold_mV, int hyst);
void setThreshold(float mV);
void setHysteresis(int hyst);
float threshold();
int hysteresis();

// TIM2 CH1 input filter, IC1F 0..15 (0 = off); filterMicros() = its length.
void setFilter(int n);
int filter();
float filterMicros();

// Lockout as a percentage of the shorter of the last two accepted periods, 0..90
// (0 = only the minimum).
void setLockout(int percent);
int lockout();

// Raw comparator output (COMP1 VALUE bit).
bool comparatorHigh();

// Accepted edges and rejected (locked-out) edges since boot (wrap at 2^32).
uint32_t edgeCount();
uint32_t rejectedCount();

// Speed from edge timestamps. Call it regularly (every 100 ms or more).
// Returns pulses/s; 0 if no edge arrived in the window or since 'timeout_ms'.
float pulseHz(uint32_t timeout_ms = 300);

}  // namespace vr
