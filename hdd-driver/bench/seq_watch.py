"""Run a sequence of steps on the hdd-driver console, with a watchdog, logging once a second.

Usage (on anduq7):  python3 - PORT RUNDIR 'JSON steps' ['note'] < seq_watch.py
Writes RUNDIR/meta.txt (date, host, firmware from the board's fw=, checkout state, steps,
note), RUNDIR/steps.json, RUNDIR/console.log (every line to and from the board, with
times) and RUNDIR/summary.txt (the once-a-second lines printed here). Copy RUNDIR into
hdd-driver/bench/runs/ and add it to runs/runs.md.
Steps (a JSON list):
  ["cmd", "CL10"]                 send a command (its reply lines are printed)
  ["wait", 3]                     poll for 3 s
  ["ramp", 900, 10, 1.3, 5]       F10, I1.3, R900; wait until the ramp reaches it; hold 5 s
  ["start"]                       E1 (refused unless the disc is still)
Abort (E0) when B's rate stays below 80 % of the ramp for 2 polls (ramp > 100 rpm), on a
firmware trip, nFAULT low, VM < 9.5 V or > 16 V. E0 on exit, also on SIGHUP/SIGTERM; then
the coast is logged for COAST_S.
"""
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time

import serial

COAST_S = 10


def bail(signum, frame):
    raise KeyboardInterrupt(f"signal {signum}")


signal.signal(signal.SIGHUP, bail)
signal.signal(signal.SIGTERM, bail)

port, rundir, steps = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
note = sys.argv[4] if len(sys.argv) > 4 else ""
os.makedirs(rundir, exist_ok=True)
ser = serial.Serial(port, 115200, timeout=0.05)
log = open(os.path.join(rundir, "console.log"), "w")
summary = open(os.path.join(rundir, "summary.txt"), "w")
with open(os.path.join(rundir, "steps.json"), "w") as fj:
    json.dump(steps, fj, indent=1)
t0 = time.time()
buf = b""
status = None
events = []
prev = None
low_count = 0


def out(msg):
    line = f"{time.time() - t0:7.1f}  {msg}"
    print(line, flush=True)
    log.write(line + "\n")
    log.flush()
    summary.write(line + "\n")
    summary.flush()


def write_meta(fw):
    def sh(cmd):
        try:
            return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10).stdout.strip()
        except Exception:
            return ""
    with open(os.path.join(rundir, "meta.txt"), "w") as fm:
        fm.write(f"date: {time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n")
        fm.write(f"host: {socket.gethostname()}\nport: {port}\n")
        fm.write(f"firmware (board fw=): {fw}\n")
        fm.write(f"checkout on this host: {sh('git -C ~/vr-exciter describe --always --dirty --abbrev=8')}\n")
        fm.write(f"note: {note}\n")
        fm.write("steps: " + json.dumps(steps) + "\n")


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


def f(d, key, default=0.0):
    try:
        return float(d.get(key, default))
    except ValueError:
        return default


def poll(check=True):
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
    if prev is not None and t > prev[1]:
        rate = (ap - prev[0]) / (t - prev[1])
        avg = (ramp + prev[2]) / 2
        err = f"{100 * (rate - avg) / avg:+5.1f}%" if avg > 20 else "      "
        out(f"{d['state']:5s} {d.get('mode', '?')} rpm {ramp:6.1f} B {rate:6.1f} {err} trk {f(d, 'trk_rpm'):6.1f}"
            f"  V {f(d, 'Vlim'):4.2f} iq {f(d, 'iqm'):5.2f} id {f(d, 'idm'):5.2f}  vm {f(d, 'vm'):5.2f} ibus {f(d, 'ibus'):4.2f}"
            f"  lrn {d.get('lrn')} lbl {d.get('lbl'):>2s} shift {d.get('shift'):>3s} marg {f(d, 'marg'):4.2f}"
            f" lcorr {f(d, 'lcorr'):4.2f} corr {d.get('corr')} miss {d.get('miss')} extra {d.get('extra')} lag {f(d, 'lag'):6.1f}")
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
    if not 9.5 <= f(d, "vm") <= 16.0:
        out(f"ABORT: VM {f(d, 'vm'):.2f} V out of 9.5..16")
        return False
    if low_count >= 2:
        out("ABORT: B rate below 80 % of the ramp for 2 s (lost the rotor?)")
        return False
    return True


try:
    pump(0.3)
    send("S")
    pump(0.5)
    write_meta(status.get("fw", "?") if status else "?")
    out(f"firmware {status.get('fw', '?') if status else '?'}; steps {json.dumps(steps)}")
    running = False
    ok = True
    for step in steps:
        kind = step[0]
        if kind == "cmd":
            send(step[1])
            pump(0.3)
            for e in events:
                out(f"{step[1]} -> {e}")
            events.clear()
        elif kind == "start":
            send("S")
            pump(0.5)
            if status is None or status["state"] != "OFF" or f(status, "apps") > 5:
                out(f"not starting: state {status and status['state']}, B {status and status.get('apps')}/s")
                ok = False
                break
            send("E1")
            running = True
            out("E1")
        elif kind == "wait":
            for _ in range(int(step[1])):
                ok = poll(check=running)
                if not ok:
                    break
        elif kind == "ramp":
            target, fr, amps, hold = step[1:5]
            send(f"F{fr}")
            send(f"I{amps}")
            send(f"R{target}")
            out(f"ramp: R{target} F{fr} I{amps}, hold {hold} s")
            start = status and float(status["rpm"].split("/")[0]) or 0
            deadline = time.time() + abs(target - start) / fr * 1.5 + 30
            while ok:
                ok = poll()
                if status and abs(float(status["rpm"].split("/")[0]) - target) < 0.01:
                    break
                if time.time() > deadline:
                    out("ABORT: ramp did not reach the target in time")
                    ok = False
            for _ in range(int(hold)):
                if not ok:
                    break
                ok = poll()
        if not ok:
            break
    if ok:
        out("sequence done")
finally:
    ser.write(b"E0\n")
    ser.flush()
    out("E0 sent")
    pump(0.5)
    events.clear()
    for _ in range(COAST_S):
        poll(check=False)
    send("E0")
    pump(0.3)
    ser.close()
    log.close()
    summary.close()
