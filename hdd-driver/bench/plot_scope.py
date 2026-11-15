"""Plot hdd-driver W scope bursts: VR_IN, I_B and the PWM pins, evenly spaced samples.

python3 plot_scope.py DIR   (reads DIR/scope_*.txt, writes DIR/plots/*.png, prints stats)
"""
import glob
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

VREF, FULL = 3300.0, 4095.0
PWM_US = 40.0  # 25 kHz
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
C_VR, C_IB = "#2a78d6", "#eb6834"
C_PWM = ("#1baf7a", "#eda100", "#e87ba4")  # IN1, IN2, IN3 (slots 3-5)
BAND = "#c3c2b7"

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": GRID,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "font.size": 9,
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.0,
})


def load(path):
    with open(path) as f:
        head = f.readline().strip()
        data = np.loadtxt(f, dtype=float)
    meta = dict(re.findall(r"(\w+)=([^ ]+)", head))
    dt = float(meta["interval_us"])
    t_ms = np.arange(len(data)) * dt / 1000.0
    vr = data[:, 0] * VREF / FULL
    ib = (data[:, 1] * VREF / FULL / 1000.0 - float(meta["ib_off"])) / 0.4
    pwm = data[:, 2].astype(int)
    return meta, dt, t_ms, vr, ib, pwm


def title(meta, k):
    st = meta["state"]
    what = "driven" if st == "RUN" else "coasting, driver off"
    return f"#{k}  {what}, ramp {float(meta['rpm']):.0f} rpm, {float(meta['interval_us']):.0f} µs/sample"


def band(ax, meta):
    thr, h = float(meta["thr"]), 10.0 * int(meta["hyst"])
    ax.axhspan(thr - h / 2, thr + h / 2, color=BAND, alpha=0.45, lw=0)
    ax.axhline(thr, color=INK2, lw=0.8, ls="--")


def stats(meta, dt, vr, pwm):
    """Noise synchronous with the PWM: fold the high-passed VR on the PWM period."""
    w = max(3, int(round(200.0 / dt)) | 1)  # ~200 us running mean = the slow VR signal
    slow = np.convolve(vr, np.ones(w) / w, mode="same")
    hf = (vr - slow)[w:-w]
    per = PWM_US / dt
    out = {"hf_rms": float(np.std(hf)), "hf_pp": float(np.ptp(hf))}
    if abs(per - round(per)) < 1e-6:
        per = int(round(per))
        idx = np.arange(len(hf)) % per
        prof = np.array([hf[idx == i].mean() for i in range(per)])
        out["pwm_sync_pp"] = float(np.ptp(prof))
        out["pwm_sync_share"] = float(np.std(prof) / np.std(hf)) if np.std(hf) else 0.0
    return out


def main(d):
    files = sorted(glob.glob(os.path.join(d, "scope_*.txt")), key=lambda p: int(re.findall(r"(\d+)", p)[-1]))
    os.makedirs(os.path.join(d, "plots"), exist_ok=True)
    caps = [load(p) for p in files]

    # Overview: VR of every burst on the same mV scale.
    fig, axs = plt.subplots(4, 2, figsize=(12, 10), sharey=True, constrained_layout=True)
    for k, (ax, (meta, dt, t, vr, ib, pwm)) in enumerate(zip(axs.flat, caps), 1):
        band(ax, meta)
        ax.plot(t, vr, color=C_VR, lw=0.7)
        ax.set_title(title(meta, k), fontsize=9, loc="left")
        ax.set_xlabel("ms")
        s = stats(meta, dt, vr, pwm)
        print(f"#{k} {meta['state']:4s} rpm {float(meta['rpm']):5.1f} dt {dt:4.0f} us: VR {vr.min():5.0f}..{vr.max():5.0f} mV "
              f"(mean {vr.mean():5.0f}), HF noise rms {s['hf_rms']:4.1f} pp {s['hf_pp']:5.1f} mV, "
              f"PWM-synchronous pp {s.get('pwm_sync_pp', float('nan')):5.1f} mV "
              f"(share {s.get('pwm_sync_share', float('nan')):.2f}), I_B {ib.min():+.2f}..{ib.max():+.2f} A")
    for ax in axs[:, 0]:
        ax.set_ylabel("VR_IN, mV")
    fig.suptitle("Sensor B (VR_IN) bursts; dashed = comparator threshold, gray = hysteresis band", x=0.01, ha="left")
    fig.savefig(os.path.join(d, "plots", "overview.png"), dpi=130)
    plt.close(fig)

    # Detail per burst: VR, I_B and PWM pins over a window, stacked on one time axis.
    for k, (meta, dt, t, vr, ib, pwm) in enumerate(caps, 1):
        for name, (t0, t1) in (("full", (t[0], t[-1])), ("zoom", (None, None))):
            if name == "zoom":
                # 400 us around the sample nearest the threshold with the steepest slope
                thr = float(meta["thr"])
                w = max(3, int(round(100.0 / dt)) | 1)
                sm = np.convolve(vr, np.ones(w) / w, mode="same")
                cross = np.where(np.diff(np.sign(sm - thr)) != 0)[0]
                cross = cross[(cross > w) & (cross < len(vr) - w)]
                c = cross[np.argmax(np.abs(np.gradient(sm)[cross]))] if len(cross) else len(vr) // 2
                t0, t1 = t[c] - 0.2, t[c] + 0.2
            m = (t >= t0) & (t <= t1)
            fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(11, 7), sharex=True, constrained_layout=True,
                                             gridspec_kw={"height_ratios": [3, 2, 1.3]})
            band(a1, meta)
            a1.plot(t[m], vr[m], color=C_VR, lw=0.9, marker="." if name == "zoom" else None, ms=3)
            a1.set_ylabel("VR_IN, mV")
            a1.set_title(title(meta, k) + ("  (zoom on a threshold crossing)" if name == "zoom" else ""), loc="left")
            a2.plot(t[m], ib[m], color=C_IB, lw=0.9)
            a2.set_ylabel("I_B, A")
            for b in range(3):
                a3.step(t[m], ((pwm[m] >> b) & 1) * 0.7 + b, where="post", color=C_PWM[b], lw=0.9)
                a3.text(t[m][0], b + 0.35, f" IN{b + 1} ", va="center", ha="right", color=INK2, fontsize=8)
            a3.set_yticks([])
            a3.set_ylim(-0.2, 2.9)
            a3.set_ylabel("PWM pins")
            a3.set_xlabel("time in burst, ms")
            fig.savefig(os.path.join(d, "plots", f"scope_{k}_{name}.png"), dpi=130)
            plt.close(fig)


if __name__ == "__main__":
    main(sys.argv[1])
