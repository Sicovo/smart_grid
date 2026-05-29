"""
Generates the theoretical Import-SMPS efficiency-vs-Vin illustration (Section 2.4).

Output: images/buck_vin_efficiency.png

This is a MODEL/SPECIFICATION figure, not measured data. It plots a synchronous
buck loss model at fixed Vbus = 10 V and fixed load current, sweeping the input
(PSU) voltage. It illustrates the argument made in Section 2.4:

  - conduction loss is independent of Vin (matched HS/LS FETs),
  - switching loss scales with Vin and Vin^2,
  - inductor ripple (hence copper loss) shrinks as Vin -> Vbus,
  - so efficiency rises monotonically as Vin is lowered toward Vbus,
  - until dropout (Vin < Vbus + Vdropout) collapses regulation.

The representative component values are illustrative; edit them as the real
bench numbers firm up.

Run from the report/ directory (or anywhere; path is resolved relative to this file):
    python scripts/generate_buck_vin_efficiency.py
"""

import os
import numpy as np
import matplotlib.pyplot as plt

# ============================================================
#  Operating point (fixed) and representative components
# ============================================================

V_BUS    = 10.0       # V  - regulated output (bus)
I_LOAD   = 1.5        # A  - delivered load current
F_SW     = 100e3      # Hz - switching frequency
R_DSON   = 0.045      # ohm- per-FET on-resistance (HS = LS, matched)
L        = 47e-6      # H  - inductor
DCR      = 0.08       # ohm- inductor copper resistance
T_RF     = 45e-9      # s  - combined rise + fall time
C_OSS    = 150e-12    # F  - output capacitance (per node)
Q_G      = 8e-9       # C  - total gate charge
V_DRV    = 5.0        # V  - gate drive rail
P_QUIES  = 0.10       # W  - fixed controller / driver quiescent loss

V_DROPOUT = 0.6       # V  - headroom needed above Vbus to stay in regulation
V_CHOSEN  = 12.0      # V  - the value the project selected

# X-axis sweep
V_IN = np.linspace(10.0, 15.0, 1000)

# Output path (always lands in report/images)
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "images",
                        "buck_vin_efficiency.png")


# ============================================================
#  Loss model
# ============================================================

P_OUT = V_BUS * I_LOAD

# Duty cycle for an ideal buck
D = V_BUS / V_IN

# Inductor ripple, then RMS inductor current
dIL   = (V_IN - V_BUS) * D / (L * F_SW)
I_rms = np.sqrt(I_LOAD**2 + (dIL**2) / 12.0)

# Conduction loss across both matched switches collapses to I_rms^2 * Rdson
P_cond = I_rms**2 * R_DSON

# Inductor copper loss
P_cu = I_rms**2 * DCR

# Switching loss: overlap term (~Vin), Coss term (~Vin^2), gate term (~const)
P_sw = (0.5 * V_IN * I_LOAD * T_RF * F_SW
        + 0.5 * C_OSS * V_IN**2 * F_SW
        + Q_G * V_DRV * F_SW)

P_loss_core = P_cond + P_cu + P_sw + P_QUIES
eta_core = 100.0 * P_OUT / (P_OUT + P_loss_core)

# Dropout collapse: smoothly crater efficiency as Vin approaches Vbus + Vdropout
v_margin = V_IN - (V_BUS + V_DROPOUT)
dropout_factor = 1.0 / (1.0 + np.exp(-v_margin / 0.06))   # logistic knee
eta = eta_core * dropout_factor


# ============================================================
#  Plot
# ============================================================

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 4.6))

# ---- Left: efficiency vs Vin ----
ax1.axvspan(V_IN.min(), V_BUS + V_DROPOUT, color="#f2c0c0", alpha=0.5,
            zorder=0, label="Dropout region")
ax1.plot(V_IN, eta, color="#1f77b4", linewidth=2.4)
ax1.axvline(V_CHOSEN, color="#2ca02c", linestyle="--", linewidth=1.4)
ax1.annotate("Selected\nVin = 12 V", xy=(V_CHOSEN, np.interp(V_CHOSEN, V_IN, eta)),
             xytext=(12.4, np.interp(V_CHOSEN, V_IN, eta) - 6),
             fontsize=9, color="#2ca02c",
             arrowprops=dict(arrowstyle="->", color="#2ca02c", lw=0.9))
ax1.set_xlabel("Input (PSU) voltage  $V_{in}$  (V)", fontsize=11)
ax1.set_ylabel("Modelled efficiency  $\\eta$  (%)", fontsize=11)
ax1.set_title("Import SMPS efficiency vs input voltage", fontsize=12)
ax1.grid(True, alpha=0.3)
ax1.set_xlim(V_IN.min(), V_IN.max())
ax1.set_ylim(0, 100)
ax1.legend(loc="lower right", fontsize=9)

# ---- Right: loss breakdown vs Vin ----
ax2.plot(V_IN, P_cond * np.ones_like(V_IN), color="#d62728", linewidth=1.8,
         label="Conduction (FET)")
ax2.plot(V_IN, P_cu, color="#9467bd", linewidth=1.8, label="Inductor copper")
ax2.plot(V_IN, P_sw, color="#ff7f0e", linewidth=1.8, label="Switching")
ax2.plot(V_IN, P_loss_core, color="#111111", linewidth=2.2, label="Total loss")
ax2.set_xlabel("Input (PSU) voltage  $V_{in}$  (V)", fontsize=11)
ax2.set_ylabel("Power loss  (W)", fontsize=11)
ax2.set_title("Loss components (model, $V_{bus}$ = 10 V, $I$ = 1.5 A)", fontsize=12)
ax2.grid(True, alpha=0.3)
ax2.set_xlim(V_BUS + V_DROPOUT, V_IN.max())
ax2.legend(loc="upper left", fontsize=9)

fig.suptitle("Synchronous buck loss model (illustrative)", fontsize=13)
plt.tight_layout(rect=[0, 0, 1, 0.96])

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
plt.savefig(OUT_PATH, dpi=200, bbox_inches="tight")
print("Saved", os.path.normpath(OUT_PATH))
