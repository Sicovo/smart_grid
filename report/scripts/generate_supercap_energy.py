"""
Generates the supercapacitor stored-energy / operating-window figure (Section 4.1).

Output: images/supercap_energy_window.png

This is a THEORETICAL figure derived from E = 1/2 C V^2 with the bank
capacitance and the firmware voltage limits (cap_smps/main.py). It shows:

  - stored energy vs terminal voltage for the 0.5 F bank,
  - the usable operating window (V_CAP_MIN = 10.5 V to the charge cutoff 15.7 V),
  - the soft-taper bands at each edge,
  - the usable energy harvested in that window.

Run:
    python scripts/generate_supercap_energy.py
"""

import os
import numpy as np
import matplotlib.pyplot as plt

# ============================================================
#  Bank + firmware limits (from cap_smps/main.py)
# ============================================================

C_BANK        = 0.5       # F   - 2 x 0.25 F in parallel
V_CAP_MIN     = 10.5      # V   - hard floor (Va > Vbus margin)
V_CAP_MAX     = 17.5      # V   - SMPS port ceiling (under 18 V cap rating)
V_TAPER_LO    = 11.0      # V   - discharge taper starts
V_TAPER_HI    = 17.0      # V   - charge taper starts
V_CHARGE_CUT  = 15.7      # V   - firmware hard charge cutoff (= cycle-test V_HI)

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "images",
                        "supercap_energy_window.png")


def energy(v):
    return 0.5 * C_BANK * v * v


# ============================================================
#  Plot
# ============================================================

V = np.linspace(0.0, V_CAP_MAX + 0.5, 1000)
E = energy(V)

fig, ax = plt.subplots(figsize=(9.2, 5.2))

# Full E-V parabola
ax.plot(V, E, color="#5ec9c0", linewidth=2.4, label="$E = \\frac{1}{2} C V^2$  (C = 0.5 F)")

# Usable window shading (floor to charge cutoff)
ax.axvspan(V_CAP_MIN, V_CHARGE_CUT, color="#cfe9e6", alpha=0.55, zorder=0,
           label="Usable window (10.5 to 15.7 V)")

# Taper bands
ax.axvspan(V_CAP_MIN, V_TAPER_LO, color="#f2c0c0", alpha=0.5, zorder=0,
           label="Discharge taper")
ax.axvspan(V_TAPER_HI, V_CAP_MAX, color="#f2d9b0", alpha=0.6, zorder=0,
           label="Charge taper")

# Endpoint markers
for v in (V_CAP_MIN, V_CHARGE_CUT, V_CAP_MAX):
    ax.plot([v, v], [0, energy(v)], color="#888888", linestyle=":", linewidth=1.0)
    ax.plot(v, energy(v), "o", color="#1f77b4", markersize=5)

# Usable energy annotation
e_lo = energy(V_CAP_MIN)
e_hi = energy(V_CHARGE_CUT)
e_max = energy(V_CAP_MAX)
ax.annotate("", xy=(V_CHARGE_CUT, e_hi), xytext=(V_CHARGE_CUT, e_lo),
            arrowprops=dict(arrowstyle="<->", color="#111111", lw=1.2))
ax.text(V_CHARGE_CUT + 0.15, (e_lo + e_hi) / 2,
        f"Usable\n{e_hi - e_lo:.0f} J", fontsize=10, va="center")
ax.text(V_CAP_MIN - 0.15, e_lo + 2, f"{e_lo:.0f} J", fontsize=9, ha="right", color="#1f77b4")
ax.text(V_CHARGE_CUT + 0.15, e_hi + 3, f"{e_hi:.0f} J", fontsize=9, color="#1f77b4")
ax.text(V_CAP_MAX + 0.05, e_max, f"{e_max:.0f} J at 17.5 V", fontsize=8.5,
        color="#666666", va="center")

ax.set_xlabel("Supercapacitor terminal voltage  $V_{cap}$  (V)", fontsize=12)
ax.set_ylabel("Stored energy  $E$  (J)", fontsize=12)
ax.set_title("Supercapacitor stored energy and usable operating window", fontsize=13)
ax.grid(True, alpha=0.3)
ax.set_xlim(0, V_CAP_MAX + 1.0)
ax.set_ylim(0, e_max * 1.12)
ax.legend(loc="upper left", fontsize=9, framealpha=0.95)

plt.tight_layout()

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
plt.savefig(OUT_PATH, dpi=200, bbox_inches="tight")
print("Saved", os.path.normpath(OUT_PATH))
