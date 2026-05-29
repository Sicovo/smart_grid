"""
Generates the EMA telemetry-filter response figure (Section 7.3).

Output: images/ema_filter_response.png

This is a THEORETICAL figure derived from the first-order exponential moving
average used on every module's display path:

    y[n] = (1 - alpha) y[n-1] + alpha x[n],   alpha = 0.05 at fs = 1 kHz

It shows the magnitude response (corner ~ 8 Hz) and the step response
(time constant ~ 20 ms, ~60 ms to 95%), justifying the choice of alpha as
a compromise between switching-ripple rejection and display lag.

Run:
    python scripts/generate_ema_response.py
"""

import os
import numpy as np
import matplotlib.pyplot as plt

# ============================================================
#  Filter parameters (from firmware)
# ============================================================

ALPHA = 0.05
FS    = 1000.0     # Hz - control tick rate

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "images",
                        "ema_filter_response.png")

# Derived characteristics
tau   = (1.0 / FS) * (1.0 - ALPHA) / ALPHA     # approx time constant (s)
fc    = 1.0 / (2.0 * np.pi * tau)              # corner frequency (Hz)


# ============================================================
#  Magnitude response of the one-pole EMA
#  H(z) = alpha / (1 - (1-alpha) z^-1),  z = exp(j 2 pi f / fs)
# ============================================================

f = np.logspace(-1, np.log10(FS / 2), 2000)
w = 2.0 * np.pi * f / FS
z = np.exp(1j * w)
H = ALPHA / (1.0 - (1.0 - ALPHA) * z**-1)
mag_db = 20.0 * np.log10(np.abs(H))


# ============================================================
#  Step response
# ============================================================

n = np.arange(0, 200)
t_ms = 1000.0 * n / FS
y = 1.0 - (1.0 - ALPHA) ** (n + 1)    # response to a unit step at n = 0


# ============================================================
#  Plot
# ============================================================

fig, (axm, axs) = plt.subplots(1, 2, figsize=(11.0, 4.4))

# ---- Magnitude response ----
axm.semilogx(f, mag_db, color="#1f77b4", linewidth=2.2)
axm.axvline(fc, color="#d62728", linestyle="--", linewidth=1.2)
axm.axhline(-3.0, color="#888888", linestyle=":", linewidth=1.0)
axm.annotate(f"$f_c$ ~ {fc:.1f} Hz", xy=(fc, -3.0), xytext=(fc * 1.3, -16),
             fontsize=9, color="#d62728",
             arrowprops=dict(arrowstyle="->", color="#d62728", lw=0.9))
axm.set_xlabel("Frequency (Hz)", fontsize=11)
axm.set_ylabel("Magnitude (dB)", fontsize=11)
axm.set_title("EMA magnitude response ($\\alpha$ = 0.05, $f_s$ = 1 kHz)", fontsize=12)
axm.grid(True, which="both", alpha=0.3)
axm.set_ylim(-40, 3)

# ---- Step response ----
axs.plot(t_ms, y, color="#2ca02c", linewidth=2.2)
axs.axhline(0.95, color="#888888", linestyle=":", linewidth=1.0)
t95 = 1000.0 * (np.log(0.05) / np.log(1.0 - ALPHA)) / FS
axs.axvline(t95, color="#d62728", linestyle="--", linewidth=1.2)
axs.annotate(f"95% at ~ {t95:.0f} ms", xy=(t95, 0.95), xytext=(t95 + 8, 0.6),
             fontsize=9, color="#d62728",
             arrowprops=dict(arrowstyle="->", color="#d62728", lw=0.9))
axs.set_xlabel("Time (ms)", fontsize=11)
axs.set_ylabel("Normalised output", fontsize=11)
axs.set_title(f"EMA step response ($\\tau$ ~ {1000*tau:.0f} ms)", fontsize=12)
axs.grid(True, alpha=0.3)
axs.set_xlim(0, t_ms.max())
axs.set_ylim(0, 1.05)

plt.tight_layout()

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
plt.savefig(OUT_PATH, dpi=200, bbox_inches="tight")
print("Saved", os.path.normpath(OUT_PATH))
