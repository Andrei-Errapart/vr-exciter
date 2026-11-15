// Minimal register-level ADC1/ADC2 driver for the G474.
//
// The Arduino core's analogRead() takes about 150 us per call on this chip,
// too slow for the control loop at high electrical frequency. This does one
// conversion in about 1-2 us and samples ADC1 and ADC2 simultaneously.
// Do not mix with analogRead(): the core stops and reconfigures the ADCs.
//
// Channels used here: VM = ADC1_IN1 (PA0), VR = ADC1_IN2 (PA1),
// I_A = ADC1_IN3 (PA2), I_BUS = ADC1_IN4 (PA3), I_B = ADC2_IN17 (PA4).
// I_B is ADC2's injected group (software-triggered): ADC2's regular group samples
// VR_IN continuously for vr_adc.
#pragma once
#include <Arduino.h>

namespace fast_adc {

constexpr int IB_CH = 17;

void begin();      // clocks, calibration, enable, configure(); takes a few ms
void configure();  // the register setup above; with both ADCs idle (the W scope restores it)

// Single conversion on ADC1 (channel 1..4). 12-bit result, 0..4095.
uint16_t read1(int ch);

// One conversion each on ADC1 (channel ch1, regular) and ADC2 (I_B, injected), started
// together so the two samples are simultaneous.
void readPair(int ch1, uint16_t& v1, uint16_t& v2);

// Sample time codes (SMPx field) and setter, for callers that change a
// channel's sample time temporarily (the VR scope).
constexpr uint32_t SMP_24_5 = 3, SMP_47_5 = 4, SMP_640_5 = 7;
void setSampleTime(ADC_TypeDef* adc, int ch, uint32_t smp);

}  // namespace fast_adc
