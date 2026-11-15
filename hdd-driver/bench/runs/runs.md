# Bench runs

One folder per run, named `YYYY-MM-DD_HHMM_what` (time on anduq7, CET). From now on
`seq_watch.py` writes each folder itself: `meta.txt` (date, host, the board's `fw=`
revision, the checkout state, the steps), `steps.json`, `console.log` (every line to and
from the board) and `summary.txt` (one line per second). Add a row here for each run.

The runs of 2026-11-15 were recorded before the firmware printed its revision. Their
firmware is given as the commit that holds the same code ("tree of X": built from the
working tree that was then committed as X).

## 2026-11-15

All runs: HDD motor with the 60-magnet disc, sensor B at 1 mm, `P4` (4 pole pairs),
start `L1000 I1.2 J1.3 A5`, voltage cap `V5`..`V6`. Supply: computer USB through the
MT3608 boost (JP1 2-3) until 17:03, 12 V USB-PD on J1 (JP1 1-2) from 17:50. The disc
cover was fitted before 17:03.

| Run | Firmware | Purpose | Result |
|-----|----------|---------|--------|
| `2026-11-15_1519_scope-300rpm` | tree of 9484506 (`W` scope) | First `W` scope bursts: VR_IN, I_B and the PWM pins at 42-300 rpm driven, and coasting (`scope_1..8.txt`, plots) | B is about ±70-110 mV at 300 rpm, one cycle per magnet. While driven only small, narrow spikes reach the ADC (2-4 mV rms); the comparator follows them. Each comparator switch steps VR_IN by about 30 mV. |
| `2026-11-15_1544_coast-revolutions` | tree of 3dfcebc (comparator filter and lockout) | Two `W60` bursts (1.3 revolutions each) while coasting from 600 rpm | One magnet position per revolution gives no midpoint crossing (59 counts per revolution with the comparator); 16 magnets earlier a trough about 140 mV deeper. `rev_analysis.py`. |
| `2026-11-15_1600_adc-detector` | trees leading to 45d308b | ADC detector: run1 fixed 1/8 low-pass to 600 rpm; run2 600 rpm hold, hysteresis and low-pass compared; run3 adaptive low-pass to 900 rpm | Fixed 1/8 counts 590 at 600 rpm (the weak magnet); 1/4 counts 600. Adaptive low-pass: within about 1 % from 45 to 900 rpm. |
| `2026-11-15_1629_coast-after-balancing` | 45d308b | `W60` bursts while coasting from 600 rpm, after the user balanced the disc | The odd magnet positions are unchanged: not runout. |
| `2026-11-15_1703_ramp-3000_usb-boost` | 45d308b | Open loop toward 3000 rpm (`ramp_watch.py`: F15/10/8, I1.2-1.4, V5.5) | Aborted at 1413 rpm: VM sagged below 9.5 V (USB boost supply). In step to there. |
| `2026-11-15_1750_ramp-3000_usb-pd` | 45d308b | Same on 12 V USB-PD, V6 | Held 1800 rpm (supply steady, under 0.76 A); lost step at the start of the 2400 rpm ramp (I1.5 step). Open loop hunts at 900-1800 rpm. |
| `2026-11-15_1808_cl-step1_learn-lock` | closed-loop development tree (vr_track first version) | Open loop to 600, learn (`CL10`), lock through 600-900-600 rpm | Lock held (margin 0.70-0.78, no corrections). The load-angle readout showed open-loop hunting of tens of degrees electrical. |
| `2026-11-15_1812_cl-step2_no-90deg` | same tree | First `C1` at 600 rpm, trim scan downward | The disc slowed in closed loop and was braked at negative trims: the learned offset was 90° off (SimpleFOC applies the voltage 90° ahead of the angle). |
| `2026-11-15_1815_cl-step2b_trim-600rpm` | tree with the +90° fix, CP 0.005, C1 starting from the open-loop voltage | Closed loop at 600 rpm, trim -30..+30 | Closed loop holds 600 rpm at 0.3-0.9 V and 0-0.35 A (open loop: 2.1-2.5 V, 1.2 A). Overshoot to 672 rpm after C1; slow speed regulation. `C0` back to open loop works. |
| `2026-11-15_1820_cl-step3_to-2430rpm` | tree of the closed-loop commit (CP 0.03, C1 at 0.3 x the open-loop voltage) | Closed loop 600 → 3000 rpm, trim scan at 1800 rpm (`seq_watch.py`) | Closed loop within ±0.3 % to about 2100 rpm (1800 rpm: 1.9 V, 0.5 A, 1.4 W from the supply). Trim optimum about -10..0°. From about 1800 rpm the swing-signature lock made false corrections (415 by the end); from 2250 rpm the voltage sat at the 5.87 V cap and the disc stalled at about 2420 rpm; phase-overcurrent trip at 2655 rpm (ramp). |
| `2026-11-15_1828_cl-to-3000` | 6be1958f (interval-signature lock, SVPWM) | Closed loop 600 → 3000 rpm, I1.5 limit above 600 rpm, V7 (first run recorded by `seq_watch.py`) | Lock correlation 0.98-1.00 at all speeds (the swing lock reached about 0.78 at most). Still label corrections from about 1790 rpm (22 by the end): real slips, about one pulse in 3600 missed or added, fixed by the lock only up to two revolutions later. Phase-overcurrent trip at about 2050 rpm. |
