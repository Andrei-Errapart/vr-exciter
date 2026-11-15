"""Per-magnet peaks in long W bursts (coasting): find the odd cycle(s) and plot them.

python3 rev_analysis.py DIR  -> prints a per-cycle table summary, writes DIR/rev_<k>.png
"""
import glob
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

C_VR, C_ODD, INK2, GRID, SURF = "#2a78d6", "#e34948", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": GRID,
                     "axes.grid": True, "grid.color": GRID, "font.size": 9,
                     "axes.spines.top": False, "axes.spines.right": False})

d = sys.argv[1]
for path in sorted(glob.glob(os.path.join(d, "scope_*.txt"))):
    k = re.findall(r"(\d+)", os.path.basename(path))[-1]
    with open(path) as f:
        meta = dict(re.findall(r"(\w+)=([^ ]+)", f.readline()))
        data = np.loadtxt(f)
    dt = float(meta["interval_us"]) * 1e-6
    vr = data[:, 0] * 3300 / 4095
    t = np.arange(len(vr)) * dt * 1000
    sm = np.convolve(vr, np.ones(5) / 5, mode="same")
    mid = np.median(sm)
    up = np.where((sm[:-1] < mid) & (sm[1:] >= mid))[0]
    cycles = []
    for a, b in zip(up[:-1], up[1:]):
        seg = sm[a:b]
        cycles.append((a, b, seg.max(), seg.min(), (b - a) * dt * 1000))
    pk = np.array([c[2] for c in cycles])
    tr = np.array([c[3] for c in cycles])
    per = np.array([c[4] for c in cycles])
    rpm = 60.0 / (np.median(per) / 1000 * 60)
    zp = (pk - np.median(pk)) / (np.std(pk) or 1)
    zt = (tr - np.median(tr)) / (np.std(tr) or 1)
    odd = [i for i in range(len(cycles)) if abs(zp[i]) > 2.5 or abs(zt[i]) > 2.5 or per[i] > 1.5 * np.median(per)]
    print(f"burst {k}: {len(cycles)} full cycles, median period {np.median(per):.3f} ms (~{rpm:.0f} rpm), "
          f"peaks {np.median(pk):.0f} mV (min {pk.min():.0f}, max {pk.max():.0f}), "
          f"troughs {np.median(tr):.0f} mV (min {tr.min():.0f}, max {tr.max():.0f})")
    for i in odd:
        a, b, p, q, pr = cycles[i]
        print(f"   odd cycle {i:2d} at {t[a]:6.1f} ms: peak {p:.0f} mV, trough {q:.0f} mV, period {pr:.2f} ms")
    if len(odd) >= 2:
        print(f"   spacing of odd cycles: {np.diff(odd)} cycles")
    fig, ax = plt.subplots(figsize=(13, 3.6), constrained_layout=True)
    ax.plot(t, vr, color=C_VR, lw=0.7)
    for i in odd:
        a, b = cycles[i][0], cycles[i][1]
        ax.axvspan(t[a], t[b], color=C_ODD, alpha=0.15, lw=0)
    ax.axhline(float(meta["thr"]), color=INK2, lw=0.8, ls="--")
    ax.set_xlabel("ms")
    ax.set_ylabel("VR_IN, mV")
    ax.set_title(f"Burst {k}, coasting ~{rpm:.0f} rpm, {float(meta['interval_us']):.0f} µs/sample: "
                 f"odd cycles shaded", loc="left")
    fig.savefig(os.path.join(d, f"rev_{k}.png"), dpi=130)
    plt.close(fig)
