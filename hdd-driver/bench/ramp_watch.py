"""Stepped spin-up with a watchdog, for the hdd-driver console.

Usage (on anduq7):  python3 - PORT LOG < ramp_watch.py
Phases: (target rpm, F ramp rpm/s, I amps, hold s). Each phase sets F and I, then R, waits
until the ramp reaches the target, holds, and goes on. Status is polled once a second.
Abort (E0) when, with the ramp above 100 rpm, B's pulse rate (from the apulses count) stays
below 80 % of the ramp speed for 2 polls in a row, or on a firmware trip, nFAULT low, or
VM < 9.5 V. E0 is always sent on exit, also on SIGHUP/SIGTERM. Then the coast is logged.
"""
import re
import signal
import sys
import time

import serial

SETUP = ["E0", "P4", "YS1", "K1", "H4", "L1000", "I1.2", "J1.3", "V6", "A5", "F15", "T0"]
PHASES = [(900, 15, 1.2, 5), (1200, 10, 1.3, 10), (1800, 8, 1.4, 10), (2400, 6, 1.5, 10), (3000, 5, 1.5, 15)]
COAST_S = 20


def bail(signum, frame):
    raise KeyboardInterrupt(f"signal {signum}")


signal.signal(signal.SIGHUP, bail)
signal.signal(signal.SIGTERM, bail)

port, logpath = sys.argv[1], sys.argv[2]
ser = serial.Serial(port, 115200, timeout=0.05)
log = open(logpath, "w")
t0 = time.time()
buf = b""
status = None  # latest parsed status line
events = []    # non-status lines since last check


def out(msg):
    line = f"{time.time() - t0:7.1f}  {msg}"
    print(line, flush=True)
    log.write(line + "\n")
    log.flush()


def pump(seconds):
    global buf, status
    end = time.time() + seconds
    while time.time() < end:
        buf += ser.read(8192)
        while b"\n" in buf:
            raw, buf = buf.split(b"\n", 1)
            line = raw.decode(errors="replace").rstrip()
            log.write(f"{time.time() - t0:7.2f} {line}\n")
            if re.match(r"(OFF|RUN|ALIGN) ", line):
                d = dict(re.findall(r"(\w+)=([^ ]+)", line))
                d["state"] = line.split()[0]
                d["t"] = time.time() - t0
                status = d
            elif line:
                events.append(line)


def send(cmd):
    log.write(f"{time.time() - t0:7.2f} >> {cmd}\n")
    ser.write((cmd + "\n").encode())


prev = None
low_count = 0


def poll_and_check(check=True):
    """One status poll; returns False to abort (only when check)."""
    global prev, low_count
    send("S")
    pump(1.0)
    for e in events:
        out(f"firmware: {e}")
    tripped = any(e.startswith("DISABLED") for e in events)
    events.clear()
    d = status
    if d is None:
        return not tripped
    ramp = float(d["rpm"].split("/")[0])
    ap, t = int(d["apulses"]), d["t"]
    rate = None
    if prev is not None and t > prev[1]:
        rate = (ap - prev[0]) / (t - prev[1])
        avg = (ramp + prev[2]) / 2
        err = f"{100 * (rate - avg) / avg:+5.1f}%" if avg > 20 else "      "
        out(f"{d['state']:5s} rpm {ramp:7.1f}  B {rate:7.1f}/s {err}  Vlim {float(d['Vlim']):4.2f}"
            f"  iq {float(d.get('iqm', 0)):5.2f}  rph {float(d.get('rph', 0)):5.2f}  vm {float(d['vm']):5.2f}"
            f"  vmmin {float(d['vmmin']):5.2f}  ibus {float(d['ibus']):5.2f}  lp 1/{d['alp']}  pp {float(d['app_mv']):5.0f} mV  ovr {d['aovr']}  nFT {d['nFT']}")
        if d["state"] == "RUN" and avg > 100 and rate < 0.8 * avg:
            low_count += 1
        else:
            low_count = 0
    prev = (ap, t, ramp)
    if not check:
        return True
    if tripped or d["state"] == "OFF":
        out("ABORT: driver is off (firmware trip)")
        return False
    if d["nFT"] == "0":
        out("ABORT: nFAULT low")
        return False
    if float(d["vm"]) < 9.5:
        out("ABORT: VM below 9.5 V")
        return False
    if float(d["vm"]) > 16.0:
        out("ABORT: VM above 16 V (energy pumped back)")
        return False
    if low_count >= 2:
        out("ABORT: B rate below 80 % of the ramp for 2 s (lost sync?)")
        return False
    return True


try:
    pump(0.3)
    for c in SETUP:
        send(c)
        pump(0.1)
    events.clear()
    send("S")
    pump(0.5)
    if status is None or status["state"] != "OFF" or float(status.get("apps", 0)) > 5:
        out(f"not starting: state {status and status['state']}, B {status and status.get('apps')}/s (disc must be still)")
        raise SystemExit(1)
    send("E1")
    out("E1")
    ok = True
    for target, f, amps, hold in PHASES:
        send(f"F{f}")
        send(f"I{amps}")
        send(f"R{target}")
        out(f"phase: R{target} F{f} I{amps}, then hold {hold} s")
        start_ramp = status and float(status["rpm"].split("/")[0]) or 0
        deadline = time.time() + abs(target - start_ramp) / f * 1.5 + 30
        while ok:
            ok = poll_and_check()
            if status and float(status["rpm"].split("/")[0]) >= target - 0.01:
                break
            if time.time() > deadline:
                out("ABORT: ramp did not reach the target in time")
                ok = False
        held = 0
        while ok and held < hold:
            ok = poll_and_check()
            held += 1
        if not ok:
            break
    if ok:
        out("all phases done")
finally:
    ser.write(b"E0\n")
    ser.flush()
    out("E0 sent")
    pump(0.5)
    events.clear()
    for _ in range(COAST_S):
        poll_and_check(check=False)
    send("E0")
    pump(0.3)
    ser.close()
    log.close()
