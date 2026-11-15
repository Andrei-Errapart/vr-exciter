"""Poll the hdd-driver status (S) fast and summarise the VR input, driver off.

Usage (on anduq7):  python3 - PORT SECONDS [SETUP_CMD...] < vr_poll.py
Prints one line per second (samples, vr min/mean/max in mV, new comparator edges, vpps),
then a histogram of all vr samples. Raw samples go to /tmp/vr_poll.csv.
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

port, secs, setup = sys.argv[1], float(sys.argv[2]), sys.argv[3:]
ser = serial.Serial(port, 115200, timeout=0.01)
pat = re.compile(r" vr=([0-9.]+) vrpm=[-0-9.]+ vpps=([-0-9.]+) edges=(\d+)")
buf = b""
samples = []  # (t, vr_mV, edges, vpps)


def read_lines():
    global buf
    buf += ser.read(8192)
    out = []
    while b"\n" in buf:
        line, buf = buf.split(b"\n", 1)
        out.append(line.decode(errors="replace").rstrip())
    return out


try:
    ser.write(b"E0\n")
    for c in setup:
        ser.write((c + "\n").encode())
        time.sleep(0.1)
    time.sleep(0.2)
    for line in read_lines():
        if not line.startswith(("OFF", "RUN", "ALIGN")):
            print("   ", line)
    t0 = time.time()
    next_s = t0
    while time.time() - t0 < secs:
        now = time.time()
        if now >= next_s:
            ser.write(b"S\n")
            next_s += 0.025
        for line in read_lines():
            m = pat.search(line)
            if m:
                samples.append((time.time() - t0, float(m.group(1)) * 1000, int(m.group(3)), float(m.group(2))))
        time.sleep(0.002)
finally:
    ser.write(b"E0\n")
    time.sleep(0.2)
    ser.close()

with open("/tmp/vr_poll.csv", "w") as f:
    f.write("t_s,vr_mV,edges,vpps\n")
    for s in samples:
        f.write(f"{s[0]:.3f},{s[1]:.0f},{s[2]},{s[3]:.1f}\n")

print(" sec   n   vr min/mean/max mV   edges+   vpps(last)")
e_prev = samples[0][2] if samples else 0
for sec in range(int(secs) + 1):
    w = [s for s in samples if sec <= s[0] < sec + 1]
    if not w:
        continue
    v = [s[1] for s in w]
    print(f"{sec:4d} {len(w):3d}   {min(v):5.0f} {sum(v) / len(v):5.0f} {max(v):5.0f}   {w[-1][2] - e_prev:6d}   {w[-1][3]:7.1f}")
    e_prev = w[-1][2]
if samples:
    print(f"total edges {samples[-1][2] - samples[0][2]} over {samples[-1][0] - samples[0][0]:.1f} s, {len(samples)} samples")
    lo = min(s[1] for s in samples)
    hist = {}
    for s in samples:
        b = int((s[1] - lo) // 10)
        hist[b] = hist.get(b, 0) + 1
    print("vr histogram (10 mV bins):")
    for b in sorted(hist):
        print(f"  {lo + 10 * b:5.0f}  {hist[b]:5d} {'#' * min(60, hist[b] // 5)}")
