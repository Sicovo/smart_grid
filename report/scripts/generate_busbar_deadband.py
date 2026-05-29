"""
Generates the bus dead-band demonstration trace (Section 2.6).

Output: images/busbar_deadband.png

NOTE: this is a SYNTHESISED trace illustrating the designed symmetric-droop
behaviour, with realistic sensor noise added. It is not a bench capture. It
shows the bus walking through three regimes as the supply/demand balance
shifts: import (bus pulled below 9.9 V, grid sources), the 9.9 to 10.1 V
dead-band (neither grid-facing module acts), and export (bus pushed above
10.1 V, export dissipates). The small steady-state offsets from the setpoints
are the droop error.

Run:
    python scripts/generate_busbar_deadband.py
"""

import os
import numpy as np
import matplotlib.pyplot as plt

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "images", "busbar_deadband.png")

rng = np.random.default_rng(42)

V_IMPORT_SET = 9.9
V_EXPORT_SET = 10.1
V_NOMINAL    = 10.0

# Time base
t = np.arange(0.0, 60.0, 0.05)

# ---- Control points (t, Vbus, I_import, I_export) per regime, with brief
#      transients at the two load steps ----
tp     = [0,    12,   13,   15,   26,   28,   29,   40,   41,   43,   54,   55,   56,   60]
vbus_c = [10.00,10.00,9.79, 9.86, 9.85, 10.05,10.04,10.02,10.25,10.16,10.15,9.92, 9.98, 9.99]
iimp_c = [0,    0,    1.30, 1.40, 1.42, 0,    0,    0,    0,    0,    0,    0,    0,    0]
iexp_c = [0,    0,    0,    0,    0,    0,    0,    0,    0.55, 0.70, 0.70, 0,    0,    0]

vbus = np.interp(t, tp, vbus_c)
iimp = np.interp(t, tp, iimp_c)
iexp = np.interp(t, tp, iexp_c)

# ---- Add realistic noise ----
vbus = vbus + rng.normal(0, 0.013, t.size)
# slow correlated wander on the bus, so it does not look like pure white noise
vbus = vbus + 0.012 * np.sin(2 * np.pi * t / 9.0 + 1.0)

iimp = iimp + rng.normal(0, 0.018, t.size)
iexp = iexp + rng.normal(0, 0.012, t.size)
iimp = np.clip(iimp, 0.0, None)
iexp = np.clip(iexp, 0.0, None)


# ============================================================
#  Plot
# ============================================================

fig, (axv, axi) = plt.subplots(2, 1, figsize=(10.0, 6.4), sharex=True,
                               gridspec_kw={"height_ratios": [1.4, 1.0]})

# ---- Top: bus voltage ----
axv.axhspan(V_IMPORT_SET, V_EXPORT_SET, color="#cccccc", alpha=0.4, zorder=0,
            label="Dead-band (9.9 to 10.1 V)")
axv.axhline(V_NOMINAL, color="gray", linestyle=":", linewidth=0.9, zorder=1)
axv.axhline(V_IMPORT_SET, color="#1f77b4", linestyle="--", linewidth=0.9, alpha=0.7)
axv.axhline(V_EXPORT_SET, color="#d62728", linestyle="--", linewidth=0.9, alpha=0.7)
axv.plot(t, vbus, color="#111111", linewidth=1.3)

axv.set_ylabel("Bus voltage  $V_{bus}$  (V)", fontsize=11)
axv.set_ylim(9.6, 10.45)
axv.grid(True, alpha=0.3)
axv.legend(loc="lower right", fontsize=8, framealpha=0.95)

# Regime annotations
axv.text(6,  10.34, "balanced\n(dead-band)", ha="center", fontsize=8.5, color="#555555")
axv.text(20, 9.66,  "grid imports\n($V_{bus}$ < 9.9 V)", ha="center", fontsize=8.5, color="#1f77b4")
axv.text(34, 10.34, "balanced", ha="center", fontsize=8.5, color="#555555")
axv.text(47, 10.38, "export dissipates\n($V_{bus}$ > 10.1 V)", ha="center", fontsize=8.5, color="#d62728")

# ---- Bottom: converter currents ----
axi.plot(t, iimp, color="#1f77b4", linewidth=1.4, label="Grid import current")
axi.plot(t, iexp, color="#d62728", linewidth=1.4, label="Export dissipation current")
axi.fill_between(t, 0, iimp, color="#1f77b4", alpha=0.15)
axi.fill_between(t, 0, iexp, color="#d62728", alpha=0.15)
axi.set_xlabel("Time (s)", fontsize=11)
axi.set_ylabel("Module current  (A)", fontsize=11)
axi.set_ylim(-0.1, 1.7)
axi.set_xlim(0, 60)
axi.grid(True, alpha=0.3)
axi.legend(loc="upper right", fontsize=8.5, framealpha=0.95)

fig.suptitle("Symmetric-droop coordination across import, dead-band and export", fontsize=13)
plt.tight_layout(rect=[0, 0, 1, 0.97])

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
plt.savefig(OUT_PATH, dpi=200, bbox_inches="tight")
print("Saved", os.path.normpath(OUT_PATH))
