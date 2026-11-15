# Bench scripts and run records

Scripts for driving the hdd-driver board over its USB console, and the records of the
runs made with them (`runs/`, indexed in `runs/runs.md`).

The board is on anduq7's USB (`/dev/serial/by-id/usb-vr-exciter_hdd-driver_*`); the
scripts run there with the system Python and pyserial, fed over ssh:

    ssh anduq7 "python3 - /dev/serial/by-id/usb-vr-exciter_hdd-driver_206536803645-if00 \
        /tmp/runs/2026-11-16_1000_name '[[\"start\"],[\"ramp\",600,15,1.2,3]]' 'note'" \
        < hdd-driver/bench/seq_watch.py

Every script sends `E0` when it ends, also when ssh drops (SIGHUP) or on an error.

| Script | Use |
|--------|-----|
| `seq_watch.py` | A sequence of steps (`start`, `cmd`, `wait`, `ramp`) with a watchdog (B below 80 % of the ramp, firmware trip, nFAULT, VM out of 9.5..16 V). Writes a run folder (meta, steps, console log, summary). Use this for new runs. |
| `ramp_watch.py` | The stepped open-loop ramp toward 3000 rpm of 2026-11-15 (phases built in). |
| `scope_console.py` | Timed console commands; saves `W` scope bursts as `scope_<k>.txt`. |
| `plot_scope.py` | Plots `scope_*.txt` (VR_IN, I_B, PWM pins) and prints noise statistics. |
| `rev_analysis.py` | Per-magnet peaks in long `W` bursts while coasting; finds the odd magnets. |
| `spin_coast.py`, `vr_poll.py`, `hdd_console.py` | Earlier helpers (spin then coast with VR logging; fast status polling; timed commands). |

## Recording a run

1. Commit the firmware first, so the board's `fw=` names a commit, not `-dirty`.
2. Run `seq_watch.py` with a run folder `/tmp/runs/YYYY-MM-DD_HHMM_what` and a note.
3. Copy the folder into `runs/` and add a row to `runs/runs.md`: firmware, purpose,
   result.
