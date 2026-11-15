// Burst capture of the VR input for a host-side "scope" (the W command).
//
// Hardware-timed, so the samples are evenly spaced (t = i * interval) whatever the
// control interrupt does:
//   - TIM6 runs at the sample rate. Its TRGO starts ADC1 and ADC2 together (dual
//     regular simultaneous mode): VR_IN on ADC1_IN2 (PA1) and I_B on ADC2_IN17 (PA4).
//     DMA1 channel 1 stores the packed pair (ADC12 common data register).
//   - The same TIM6 update requests DMA1 channel 2, which copies GPIOA->IDR: the pin
//     levels of the TIM1 PWM outputs PA8, PA9, PA10 (IN1..IN3) at the tick. The ADCs
//     sample during the 1.1 us after the tick.
// The capture blocks the main loop (protection checks, current regulator) until it and
// its printout are done; the control interrupt keeps the field turning and the
// DRV8313's own OCP stays active. vr_adc is paused for the burst; afterwards the ADCs
// return to fast_adc's setup (fast_adc::configure()) and vr_adc resumes.
#pragma once
#include <Arduino.h>

namespace vr_scope {

constexpr int MAX_SAMPLES = 4000;

struct Result {
  int n;               // samples captured (0 = timeout)
  float interval_us;   // actual spacing, from the timer's period
  uint32_t edges;      // VR comparator edges TIM2 counted during the burst
};

// Capture n samples interval_us apart (at least MIN_INTERVAL_US).
constexpr float MIN_INTERVAL_US = 2.0f;
Result capture(float interval_us, int n = MAX_SAMPLES);

// Print the last capture, one sample per line: "vr_raw ib_raw pwm"
// (12-bit ADC counts; pwm bits: 1 = PA8 (IN1), 2 = PA9 (IN2), 4 = PA10 (IN3)).
void print(Stream& out);

}  // namespace vr_scope
