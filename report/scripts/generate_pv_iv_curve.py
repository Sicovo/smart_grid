"""
Generates the illustrative PV I-V / P-V characteristic figure (Section 3.1).

Output: images/pv_iv_curve.png

This is a CONCEPTUAL single-diode-model illustration, NOT a measured sweep of
the project's panel. It shows the I-V and P-V curves at a few irradiance levels
and marks the maximum power point (MPP) that the MPPT algorithm must track. The
panel ratings used as anchors (Voc ~ 8.5 V, Isc ~ 1.0 A, ~8 W) come from the
project brief; the curve shape comes from the standard single-diode equation.

The measured per-panel I-V sweep (the real characterisation data) is a separate
experimental figure and is NOT produced by this script.

Run:
    python scripts/generate_pv_iv_curve.py
"""

import os
import numpy as np
import matplotlib.pyplot as plt

# ============================================================
#  Single-diode model anchors (from the brief)
# ============================================================

I_SC_FULL = 1.0      # A   - short-circuit current at full irradiance
V_OC      = 8.5      # V   - open-circuit voltage
N_VT      = 0.55     # V   - diode ideality * thermal voltage (shape parameter)
R_S       = 0.4      # ohm - series resistance (rounds the knee)

IRRADIANCE = [1.0, 0.75, 0.5, 0.25]   # fractions of full sun
COLORS     = ["#d62728", "#ff7f0e", "#2ca02c", "#1f77b4"]

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "images",
                        "pv_iv_curve.png")


def pv_current(v, irr):
    """Single-diode model: I = Iph - I0 (exp((V + I Rs)/nVt) - 1).
    Iph scales with irradiance; I0 fixed so that V_oc is held at full sun.
    Solved by simple fixed-point iteration on I (adequate for plotting)."""
    i_ph = I_SC_FULL * irr
    i_0  = I_SC_FULL / (np.exp(V_OC / N_VT) - 1.0)
    i = np.full_like(v, i_ph)
    for _ in range(60):
        i = i_ph - i_0 * (np.exp((v + i * R_S) / N_VT) - 1.0)
    return np.clip(i, 0.0, None)


# ============================================================
#  Plot
# ============================================================

fig, (axiv, axpv) = plt.subplots(1, 2, figsize=(11.0, 4.6))
V = np.linspace(0.0, V_OC, 1000)

for irr, col in zip(IRRADIANCE, COLORS):
    I = pv_current(V, irr)
    P = V * I

    axiv.plot(V, I, color=col, linewidth=2.0, label=f"{int(irr*100)}% sun")
    axpv.plot(V, P, color=col, linewidth=2.0, label=f"{int(irr*100)}% sun")

    # Mark the MPP on both panels
    k = int(np.argmax(P))
    axiv.plot(V[k], I[k], "o", color=col, markersize=5)
    axpv.plot(V[k], P[k], "o", color=col, markersize=5)
    if irr == 1.0:
        axpv.annotate(f"MPP\n({V[k]:.1f} V, {P[k]:.1f} W)",
                      xy=(V[k], P[k]), xytext=(V[k] - 3.4, P[k] - 0.4),
                      fontsize=9, color=col,
                      arrowprops=dict(arrowstyle="->", color=col, lw=0.9))

# I-V panel cosmetics
axiv.set_xlabel("Panel voltage  $V_{pv}$  (V)", fontsize=11)
axiv.set_ylabel("Panel current  $I_{pv}$  (A)", fontsize=11)
axiv.set_title("I-V characteristic", fontsize=12)
axiv.grid(True, alpha=0.3)
axiv.set_xlim(0, V_OC)
axiv.set_ylim(0, I_SC_FULL * 1.1)
axiv.legend(loc="lower left", fontsize=9)

# P-V panel cosmetics
axpv.set_xlabel("Panel voltage  $V_{pv}$  (V)", fontsize=11)
axpv.set_ylabel("Panel power  $P_{pv}$  (W)", fontsize=11)
axpv.set_title("P-V characteristic and MPP locus", fontsize=12)
axpv.grid(True, alpha=0.3)
axpv.set_xlim(0, V_OC)
axpv.legend(loc="upper right", fontsize=9)

fig.suptitle("PV panel single-diode model (illustrative, not measured)", fontsize=13)
plt.tight_layout(rect=[0, 0, 1, 0.96])

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
plt.savefig(OUT_PATH, dpi=200, bbox_inches="tight")
print("Saved", os.path.normpath(OUT_PATH))
