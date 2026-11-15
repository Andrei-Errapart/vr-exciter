// VR pickup B, detected from ADC samples instead of the comparator.
//
// ADC2's regular group samples VR_IN (ADC2_IN2 = PA1), triggered by TIM1's update
// (TRGO). SimpleFOC runs TIM1 center-aligned with RCR = 1, so that is one sample per
// PWM period (25 kHz), at a turn of the counter, half a period away from the output
// switching that puts spikes on VR_IN. DMA1 channel 3 writes the samples into a circular
// buffer; poll() (from the main loop) works through the new ones. The time of a sample is
// its index divided by the sample rate, which comes from TIM1's registers. No interrupt:
// ADC1/ADC2 share one, and SimpleFOC's current-sense code already defines its handler.
// fast_adc reads I_B on ADC2's injected group, which briefly delays a VR conversion.
//
// Per sample:
//   1. median of the last 3 samples (removes single-sample spikes);
//   2. first-order low-pass, y += (x - y) / 2^shift. Its time constant (2^shift
//      samples) is kept at most a tenth of the pulse spacing, up to 1/8 (about 530 Hz)
//      at low speed and standstill, where the noise (6-7 mV pp) needs it; 1/4 at
//      600 rpm, none from about 1500 rpm. A fixed 1/8 smoothed away the weak magnet's
//      pulse at 600 rpm;
//   3. peak/trough detection: a peak is confirmed once y has fallen hyst below the
//      running maximum, a trough once y has risen hyst above the running minimum.
//      hyst = max(floor, hyst% of the recent peak-to-peak), so it follows the
//      amplitude, which grows with speed (±85 mV at 340 rpm, ±130 at 600) and differs between
//      magnets (one is about 90 mV weaker at 340 rpm);
//   4. one pulse per magnet: the rising crossing of the midpoint between the last
//      peak and the trough just confirmed, interpolated between the two samples.
// With no extreme confirmed for DECAY_MS the peak-to-peak estimate halves, so the
// detector follows a slowing disc's shrinking pulses down to the floor.
#pragma once
#include <Arduino.h>

namespace vr_adc {

// Call after fast_adc::begin() and the driver's init (TIM1 running).
void begin();
// Call from the main loop as often as possible; the buffer holds about 40 ms.
void poll();
// Stop and restart the sampling (the W scope reconfigures the ADCs).
void pause();
void resume();

void setHystPercent(int pct);  // 5..45 % of the peak-to-peak, default 30
// Low-pass y += (x - y) / 2^shift, shift adapted to the speed (time constant at most a
// tenth of the pulse spacing) up to this maximum (0..5, default 3: 1/8, used at low speed).
void setLowPassMaxShift(int shift);
int lowPassMaxShift();
int lowPassShift();  // in use now
int hystPercent();
void setFloorMv(float mV);     // smallest hysteresis, 1..100 mV, default 10
float floorMv();

uint32_t pulseCount();                     // pulses (midpoint crossings) since boot
float pulseHz(uint32_t timeout_ms = 300);  // like vr::pulseHz: call every 100 ms or more
float ppMv();                              // recent peak-to-peak (smoothed)
float levelMv();                           // filtered VR_IN now
uint32_t sampleCount();                    // samples processed since boot
float sampleHz();                          // the sample rate, from TIM1
uint32_t overruns();                       // times poll() came too late (samples lost)

}  // namespace vr_adc
