// VR pickup coil -> speed measurement.
//
// VR_IN (PA1) goes to COMP1's non-inverting input. The threshold is DAC3 CH1,
// an on-chip DAC with no pin, on COMP1's inverting input. COMP1's output feeds
// TIM2 input capture 1 (TI1SEL = comp1_out), so no pin or EXTI is needed. The
// 32-bit TIM2 timestamps every rising edge.
#pragma once
#include <Arduino.h>

namespace vr {

// Call once. Threshold in mV is the comparator trip level (the coil is biased
// at 1.65 V, so about 1650); hyst 0..7 = 0..70 mV in 10 mV steps.
void begin(float threshold_mV, int hyst);
void setThreshold(float mV);
void setHysteresis(int hyst);
float threshold();
int hysteresis();

// Raw comparator output (COMP1 VALUE bit).
bool comparatorHigh();

// Edges counted since boot (wraps at 2^32).
uint32_t edgeCount();

// Speed from edge timestamps. Call it regularly (every 100 ms or more).
// Returns pulses/s; 0 if no edge arrived in the window or since 'timeout_ms'.
float pulseHz(uint32_t timeout_ms = 300);

}  // namespace vr
