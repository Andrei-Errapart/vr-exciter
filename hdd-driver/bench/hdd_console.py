"""Run a timed list of console commands against the hdd-driver firmware and print every line.

Usage (on anduq7):  python3 - PORT STEP... < hdd_console.py
Each STEP is "CMD@SECONDS": send CMD (may be empty), then listen for SECONDS.
The driver is always sent E0 on exit, also on SIGHUP/SIGTERM (ssh dropped) and errors.
"""
import signal
import sys
import time

import serial


def bail(signum, frame):
    raise KeyboardInterrupt(f"signal {signum}")


signal.signal(signal.SIGHUP, bail)
signal.signal(signal.SIGTERM, bail)

port, steps = sys.argv[1], sys.argv[2:]
ser = serial.Serial(port, 115200, timeout=0.05)
t0 = time.time()
buf = b""


def pump(seconds: float) -> None:
    global buf
    end = time.time() + seconds
    while time.time() < end:
        buf += ser.read(4096)
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            print(f"{time.time() - t0:7.2f}  {line.decode(errors='replace').rstrip()}", flush=True)


def send(cmd: str) -> None:
    print(f"{time.time() - t0:7.2f} >> {cmd}", flush=True)
    ser.write((cmd + "\n").encode())


try:
    pump(0.5)
    for step in steps:
        cmd, _, secs = step.rpartition("@")
        if cmd:
            send(cmd)
        pump(float(secs))
finally:
    ser.write(b"E0\n")
    ser.flush()
    pump(0.5)
    ser.close()
