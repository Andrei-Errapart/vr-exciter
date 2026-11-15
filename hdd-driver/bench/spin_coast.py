"""Spin up open-loop, then switch the driver off and log the VR input while the disc coasts.

Usage (on anduq7):  python3 - PORT RUN_S COAST_S SETUP_CMD... < spin_coast.py
SETUP_CMDs are sent first (driver off), then E1. Status is polled at 2 Hz during the run and at
40 Hz during the coast. Per-second summary of each phase; raw samples in /tmp/spin_coast.csv.
The driver gets E0 on exit, also on SIGHUP/SIGTERM.
"""
import re
import signal
import sys
import time

import serial


def bail(signum, frame):
    raise KeyboardInterrupt(f"signal {signum}")


signal.signal(signal.SIGHUP, bail)
signal.signal(signal.SIGTERM, bail)

port, run_s, coast_s, setup = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4:]
ser = serial.Serial(port, 115200, timeout=0.01)
num = r"([-0-9.]+)"
fields = ("rpm", "Vlim", "rph", "vr", "vpps", "edges")
pats = {k: re.compile(rf" {k}={num}") for k in fields}
buf = b""
rows = []  # (phase, t, dict)


def read_lines():
    global buf
    buf += ser.read(8192)
    out = []
    while b"\n" in buf:
        line, buf = buf.split(b"\n", 1)
        out.append(line.decode(errors="replace").rstrip())
    return out


def poll(phase, secs, period, t0):
    end = time.time() + secs
    nxt = time.time()
    while time.time() < end:
        if time.time() >= nxt:
            ser.write(b"S\n")
            nxt += period
        for line in read_lines():
            if line.startswith(("OFF", "RUN", "ALIGN")):
                d = {k: float(m.group(1)) for k, p in pats.items() if (m := p.search(line))}
                d["state"] = line.split()[0]
                rows.append((phase, time.time() - t0, d))
            elif line:
                print(f"{time.time() - t0:7.2f}  {line}", flush=True)
        time.sleep(0.002)


try:
    ser.write(b"E0\n")
    for c in setup:
        ser.write((c + "\n").encode())
        time.sleep(0.1)
    time.sleep(0.3)
    read_lines()
    t0 = time.time()
    ser.write(b"E1\n")
    poll("run", run_s, 0.5, t0)
    ser.write(b"E0\n")
    t_off = time.time() - t0
    poll("coast", coast_s, 0.2, t0)  # slow: each S samples VR_IN with the ADC and kicks the comparator
finally:
    ser.write(b"E0\n")
    time.sleep(0.2)
    ser.close()

with open("/tmp/spin_coast.csv", "w") as f:
    f.write("phase,t_s,state,rpm,Vlim,rph,vr,vpps,edges\n")
    for ph, t, d in rows:
        f.write(f"{ph},{t:.3f},{d.get('state')},{','.join(str(d.get(k, '')) for k in fields)}\n")

print("RUN (2 Hz): t  state  rpm  Vlim  rph  vpps")
for ph, t, d in rows:
    if ph == "run":
        print(f"  {t:5.1f} {d['state']:5s} {d.get('rpm', 0):6.1f} {d.get('Vlim', 0):5.2f} {d.get('rph', 0):6.3f} {d.get('vpps', 0):8.1f}")
print(f"COAST from {t_off:.1f} s (40 Hz): sec  n  vr min/mean/max mV  edges+  vpps median")
coast = [(t - t_off, d) for ph, t, d in rows if ph == "coast"]
e_prev = coast[0][1]["edges"] if coast else 0
for sec in range(int(coast_s) + 1):
    w = [d for t, d in coast if sec <= t < sec + 1]
    if not w:
        continue
    v = [d["vr"] * 1000 for d in w]
    vp = sorted(d["vpps"] for d in w)
    print(f"  {sec:3d} {len(w):3d}  {min(v):5.0f} {sum(v) / len(v):5.0f} {max(v):5.0f}  {int(w[-1]['edges'] - e_prev):6d}  {vp[len(vp) // 2]:7.1f}")
    e_prev = w[-1]["edges"]
