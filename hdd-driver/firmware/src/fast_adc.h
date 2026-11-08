// Minimal register-level ADC1/ADC2 driver for the G474.
//
// The Arduino core's analogRead() takes about 150 us per call on this chip,
// too slow for the control loop at high electrical frequency. This does one
// conversion in about 1-2 us and samples ADC1 and ADC2 simultaneously.
// Do not mix with analogRead(): the core stops and reconfigures the ADCs.
//
// Channels used here: VM = ADC1_IN1 (PA0), VR = ADC1_IN2 (PA1),
// I_A = ADC1_IN3 (PA2), I_BUS = ADC1_IN4 (PA3), I_B = ADC2_IN17 (PA4).
#pragma once
#include <Arduino.h>

namespace fast_adc {

void begin();  // clocks, calibration, enable; takes a few ms

// Single conversion on ADC1 (channel 1..4). 12-bit result, 0..4095.
uint16_t read1(int ch);

// One conversion each on ADC1 (channel ch1) and ADC2 (channel 17), started
// together so the two samples are simultaneous.
void readPair(int ch1, uint16_t& v1, uint16_t& v2);

}  // namespace fast_adc
