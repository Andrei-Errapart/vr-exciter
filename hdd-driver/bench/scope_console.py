"""Timed console commands for the hdd-driver; W scope bursts are saved to files.

Usage (on anduq7):  python3 - PORT OUTDIR STEP... < scope_console.py
Each STEP is "CMD@SECONDS": send CMD (may be empty), then listen for SECONDS.
A burst printed between "scope begin ..." and "scope end" goes to OUTDIR/scope_<k>.txt
(header line first) and is summarised here instead of printed. Status lines (S) print in
full. The driver gets E0 on exit, also on SIGHUP/SIGTERM and errors.
"""
import os
import signal
import sys
import time

import serial


def bail(signum, frame):
    raise KeyboardInterrupt(f"signal {signum}")


signal.signal(signal.SIGHUP, bail)
signal.signal(signal.SIGTERM, bail)

port, outdir, steps = sys.argv[1], sys.argv[2], sys.argv[3:]
os.makedirs(outdir, exist_ok=True)
ser = serial.Serial(port, 115200, timeout=0.05)
t0 = time.time()
buf = b""
scope = None  # list of lines while inside a burst
k = 0


def handle(line: str) -> None:
    global scope, k
    if line.startswith("scope begin"):
        scope = [line]
        return
    if scope is not None:
        if line == "scope end":
            k += 1
            path = os.path.join(outdir, f"scope_{k}.txt")
            with open(path, "w") as f:
                f.write("\n".join(scope) + "\n")
            vr = [int(l.split()[0]) for l in scope[1:] if l[:1].isdigit()]
            mv = [v * 3300 / 4095 for v in vr]
            print(f"{time.time() - t0:7.2f}  {scope[0]}", flush=True)
            if mv:
                print(f"{time.time() - t0:7.2f}  -> {path}: {len(vr)} samples, vr {min(mv):.0f}..{max(mv):.0f} mV", flush=True)
            scope = None
        else:
            scope.append(line)
        return
    print(f"{time.time() - t0:7.2f}  {line}", flush=True)


def pump(seconds: float) -> None:
    global buf
    end = time.time() + seconds
    while time.time() < end:
        buf += ser.read(16384)
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            handle(line.decode(errors="replace").rstrip())


try:
    pump(0.3)
    for step in steps:
        cmd, _, secs = step.rpartition("@")
        if cmd:
            print(f"{time.time() - t0:7.2f} >> {cmd}", flush=True)
            ser.write((cmd + "\n").encode())
        pump(float(secs))
finally:
    ser.write(b"E0\n")
    ser.flush()
    pump(0.5)
    ser.close()
