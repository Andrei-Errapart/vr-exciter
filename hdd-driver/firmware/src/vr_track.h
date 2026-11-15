// Rotor angle from sensor B: magnet labels, a learned signature lock, and the
// electrical angle for closed-loop commutation.
//
// vr_adc reports one pulse per magnet (the rising midpoint crossing, its time corrected
// for the detector's filter delays) and the pulse's swing (last peak - this trough).
// Each pulse gets a label 0..59. Learning (at a steady open-loop speed, over a few
// revolutions) records:
//   - the interval signature, for the lock: each interval relative to its neighbours,
//     set by the magnets' spacing and so independent of speed (the pulse swings, used
//     first, changed with the detector's filter and gave false corrections);
//   - each label's mechanical angle, from the mean interval before it (the magnets are
//     not evenly spaced to the last 0.1 mm);
//   - the electrical offset: the open-loop field angle at each label's pulse, + 90
//     degrees (SimpleFOC applies the voltage 90 degrees ahead of the angle it is given,
//     and at light load the magnet lines up with the voltage), minus pole_pairs x the
//     label's angle. The magnet lags the field by the load angle, so the offset includes
//     that lag; the closed-loop trim takes it out.
// Lock: once per revolution the last 60 intervals' signature is correlated with the
// learned one at all 60 shifts. A shift other than 0 means a pulse was missed or added;
// seen twice in a row, the labels are corrected.
// Each pulse is checked against the expected interval to the next magnet: under half a
// gap it is ignored as spurious, about two gaps late the labels move on by two (a pulse
// was missed). The lock check is the backstop.
// Angle: label angle + speed x time since the pulse, at most 1.5 gaps ahead (so a
// stopping rotor does not run away), plus a lead for the PWM's actuation delay.
// Times are in 1/256 of an ADC sample (vr_adc's time base).
#pragma once
#include <Arduino.h>

namespace vr_track {

constexpr int MAGNETS = 60;

void begin(int pole_pairs, float sample_hz);
void setPolePairs(int pole_pairs);

// ISR side (control interrupt). setField(): the open-loop field angle just applied
// and its speed, both electrical; used by learning and the lag readout.
void setField(float theta_e, float omega_e);
void onPulse(uint32_t t256, int32_t swing16, uint32_t now256);
float electricalAngle(uint32_t now256);
bool angleValid(uint32_t now256);  // a recent pulse and a speed estimate

// Main-loop side.
bool startLearning(int revolutions);  // false if already learning
void poll();                          // finishes learning, runs the lock check
bool learning();
bool learned();
bool locked();                        // learned, last check at shift 0, good margin
float speedRpm();                     // from the last quarter revolution
uint32_t pulseCount();
int label();
int lastShift();
float lastMargin();
float lastCorrelation();             // best correlation of the last lock check (1 = perfect)
uint32_t missedPulses();             // pulses found missing (two gaps late) and skipped over
uint32_t extraPulses();              // pulses ignored as spurious (under half a gap)
int worstLabel(bool missed, uint32_t* count);  // the label with the most missed / extra
uint32_t corrections();
float offsetDeg();
float offsetSpreadDeg();              // how consistent the per-label offsets were
float fieldLagDeg(uint32_t now256);   // open loop: load angle (field vector - magnet)
void setTrimDeg(float deg);
float trimDeg();
void setLeadUs(float us);
float leadUs();

}  // namespace vr_track
