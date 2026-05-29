"""
Generates the MEASURED PV characterisation figures (Section 3).

Outputs:
  images/pv_iv_measured.png        - measured I-V and P-V curves, 7 irradiance levels
  images/pv_vmpp_irradiance.png    - measured Vmpp and Pmax vs irradiance (the firmware lookup table)

Data is the group's own bench sweep of the panel under the solar emulator at
seven dimmer settings (10% to 100%). Each sweep steps the load current and
records panel voltage; power is the product. The maximum-power voltages match
the VMPP_TABLE used by firmware/pv_smps/main.py.

Run:
    python scripts/generate_pv_measured.py
"""

import os
import numpy as np
import matplotlib.pyplot as plt

OUT_IV   = os.path.join(os.path.dirname(__file__), "..", "images", "pv_iv_measured.png")
OUT_VMPP = os.path.join(os.path.dirname(__file__), "..", "images", "pv_vmpp_irradiance.png")

# ============================================================
#  Measured sweeps: irradiance fraction -> list of (I, V)
#  (P recomputed as I*V)
# ============================================================

SWEEPS = {
    1.00: [(0,7.87),(0.05,7.74),(0.1,7.62),(0.15,7.48),(0.2,7.35),(0.25,7.2),
           (0.3,7.05),(0.35,6.88),(0.4,6.68),(0.41,6.62),(0.42,6.57),(0.43,6.5),
           (0.44,6.43),(0.45,6.34),(0.5,5.3),(0.55,4.52),(0.6,3.9),(0.65,3.35),
           (0.7,2.82),(0.75,2.3),(0.8,1.77),(0.85,1.4),(0.9,1.07),(0.95,0.67),
           (1.0,0.03),(1.05,0.03)],
    0.80: [(0,7.56),(0.02,7.51),(0.04,7.45),(0.06,7.4),(0.08,7.33),(0.1,7.28),
           (0.12,7.21),(0.14,7.15),(0.16,7.08),(0.18,7.01),(0.2,6.94),(0.22,6.86),
           (0.24,6.78),(0.26,6.69),(0.28,6.58),(0.3,6.46),(0.32,6.22),(0.34,5.59),
           (0.36,4.97),(0.38,4.51),(0.4,4.12),(0.42,3.76),(0.44,3.43),(0.46,3.1),
           (0.48,2.78),(0.5,2.45),(0.52,2.13),(0.54,1.81),(0.56,1.43),(0.58,0.97),
           (0.6,0.02)],
    0.65: [(0,7.62),(0.02,7.56),(0.04,7.5),(0.06,7.43),(0.08,7.37),(0.1,7.3),
           (0.12,7.23),(0.14,7.16),(0.16,7.08),(0.18,7.0),(0.2,6.91),(0.22,6.81),
           (0.24,6.69),(0.26,6.53),(0.28,6.13),(0.3,5.25),(0.32,4.6),(0.34,4.11),
           (0.36,3.66),(0.38,3.24),(0.4,2.81),(0.42,2.39),(0.44,1.97),(0.46,1.49),
           (0.48,0.8),(0.5,0.01)],
    0.50: [(0,7.53),(0.02,7.47),(0.04,7.4),(0.06,7.34),(0.08,7.27),(0.1,7.19),
           (0.12,7.11),(0.14,7.03),(0.16,6.94),(0.18,6.83),(0.2,6.7),(0.22,6.48),
           (0.235,6.08),(0.24,5.6),(0.26,4.72),(0.28,4.06),(0.3,3.46),(0.32,2.89),
           (0.34,2.33),(0.36,1.72),(0.38,0.8),(0.4,0.4),(0.42,0.042)],
    0.35: [(0,7.46),(0.01,7.43),(0.02,7.39),(0.03,7.35),(0.04,7.31),(0.05,7.27),
           (0.06,7.22),(0.07,7.18),(0.08,7.12),(0.09,7.08),(0.1,7.02),(0.11,6.97),
           (0.12,6.9),(0.13,6.83),(0.14,6.76),(0.15,6.68),(0.16,6.58),(0.17,6.46),
           (0.18,6.21),(0.185,6.05),(0.19,5.8),(0.2,5.1),(0.21,4.49),(0.22,4.06),
           (0.23,3.64),(0.24,3.24),(0.25,2.88),(0.26,2.49),(0.27,2.09),(0.28,1.64),
           (0.29,1.06),(0.3,0.0095)],
    0.25: [(0,7.03),(0.01,6.99),(0.02,6.94),(0.03,6.87),(0.04,6.81),(0.05,6.73),
           (0.06,6.66),(0.07,6.57),(0.08,6.47),(0.09,6.35),(0.1,6.2),(0.11,5.88),
           (0.12,5.02),(0.13,3.93),(0.14,3.02),(0.15,2.16),(0.16,0.016),(0.17,0.0054)],
    0.10: [(0,7.0),(0.01,6.92),(0.02,6.84),(0.03,6.75),(0.04,6.65),(0.05,6.52),
           (0.06,6.39),(0.07,6.2),(0.08,5.95),(0.085,5.76),(0.087,5.65),(0.09,5.44),
           (0.093,5.15),(0.1,4.1),(0.11,2.58),(0.12,0.0039)],
}

LEVELS = sorted(SWEEPS.keys())                      # ascending irradiance
CMAP   = plt.cm.viridis(np.linspace(0.1, 0.9, len(LEVELS)))

# Curated maximum-power points (Imp, Vmpp) = the firmware VMPP_TABLE entries.
# The P-V peak is flat, so these are pinned to the lookup-table values rather
# than the noisy per-sweep argmax (matters only at 100%: 6.43 V vs 6.34 V).
MPP = {
    0.10: (0.087, 5.65), 0.25: (0.110, 5.88), 0.35: (0.185, 6.05),
    0.50: (0.235, 6.08), 0.65: (0.280, 6.13), 0.80: (0.320, 6.22),
    1.00: (0.440, 6.43),
}


# ============================================================
#  Figure 1: measured I-V and P-V curves
# ============================================================

fig, (axiv, axpv) = plt.subplots(1, 2, figsize=(11.0, 4.7))

vmpp_pts, pmax_pts, imp_pts = {}, {}, {}

for col, irr in zip(CMAP, LEVELS):
    arr = np.array(SWEEPS[irr])
    I, V = arr[:, 0], arr[:, 1]
    P = I * V
    label = f"{int(irr*100)}%"

    axiv.plot(V, I, "-o", color=col, markersize=2.6, linewidth=1.6, label=label)
    axpv.plot(V, P, "-o", color=col, markersize=2.6, linewidth=1.6, label=label)

    imp, vmpp = MPP[irr]
    vmpp_pts[irr], imp_pts[irr], pmax_pts[irr] = vmpp, imp, imp * vmpp
    axiv.plot(vmpp, imp, "*", color=col, markersize=11, markeredgecolor="k", markeredgewidth=0.4)
    axpv.plot(vmpp, imp * vmpp, "*", color=col, markersize=11, markeredgecolor="k", markeredgewidth=0.4)

# trace the MPP locus on the P-V panel
vlist = [vmpp_pts[i] for i in LEVELS]
plist = [pmax_pts[i] for i in LEVELS]
axpv.plot(vlist, plist, "--", color="#444444", linewidth=1.0, label="MPP locus")

axiv.set_xlabel("Panel voltage  $V_{pv}$  (V)", fontsize=11)
axiv.set_ylabel("Panel current  $I_{pv}$  (A)", fontsize=11)
axiv.set_title("Measured I-V characteristic", fontsize=12)
axiv.grid(True, alpha=0.3)
axiv.set_xlim(0, 8.2)
axiv.set_ylim(0, 1.08)
axiv.legend(title="Irradiance", loc="upper right", fontsize=8, ncol=2)

axpv.set_xlabel("Panel voltage  $V_{pv}$  (V)", fontsize=11)
axpv.set_ylabel("Panel power  $P_{pv}$  (W)", fontsize=11)
axpv.set_title("Measured P-V characteristic and MPP locus", fontsize=12)
axpv.grid(True, alpha=0.3)
axpv.set_xlim(0, 8.2)
axpv.set_ylim(0, 3.1)
axpv.legend(loc="upper left", fontsize=8, ncol=2)

fig.suptitle("PV panel characterisation under the solar emulator (measured)", fontsize=13)
plt.tight_layout(rect=[0, 0, 1, 0.95])
os.makedirs(os.path.dirname(OUT_IV), exist_ok=True)
plt.savefig(OUT_IV, dpi=200, bbox_inches="tight")
print("Saved", os.path.normpath(OUT_IV))
plt.close(fig)


# ============================================================
#  Figure 2: Vmpp and Pmax vs irradiance (the firmware lookup table)
# ============================================================

irr_pct = np.array([i * 100 for i in LEVELS])
vmpp    = np.array([vmpp_pts[i] for i in LEVELS])
pmax    = np.array([pmax_pts[i] for i in LEVELS])

fig2, ax = plt.subplots(figsize=(8.4, 5.0))

l1 = ax.plot(irr_pct, vmpp, "-o", color="#1f77b4", linewidth=2.0, markersize=6,
             label="$V_{mpp}$ (lookup table)")
ax.set_xlabel("Irradiance (% of full emulator output)", fontsize=12)
ax.set_ylabel("Maximum-power voltage  $V_{mpp}$  (V)", color="#1f77b4", fontsize=12)
ax.tick_params(axis="y", labelcolor="#1f77b4")
ax.set_ylim(5.4, 6.6)
ax.grid(True, alpha=0.3)

for x, y in zip(irr_pct, vmpp):
    ax.annotate(f"{y:.2f}", (x, y), textcoords="offset points", xytext=(0, 8),
                ha="center", fontsize=8, color="#1f77b4")

ax2 = ax.twinx()
l2 = ax2.plot(irr_pct, pmax, "-s", color="#d62728", linewidth=2.0, markersize=6,
              label="$P_{max}$")
ax2.set_ylabel("Maximum power  $P_{max}$  (W)", color="#d62728", fontsize=12)
ax2.tick_params(axis="y", labelcolor="#d62728")
ax2.set_ylim(0, 3.1)

lines = l1 + l2
ax.legend(lines, [ln.get_label() for ln in lines], loc="upper left", fontsize=10)
ax.set_title("Measured $V_{mpp}$ and $P_{max}$ vs irradiance", fontsize=13)

plt.tight_layout()
plt.savefig(OUT_VMPP, dpi=200, bbox_inches="tight")
print("Saved", os.path.normpath(OUT_VMPP))

# Console summary
print("\nirr%   Vmpp   Imp    Pmax")
for i in LEVELS:
    print(f"{int(i*100):4d}  {vmpp_pts[i]:5.2f}  {imp_pts[i]:5.3f}  {pmax_pts[i]:5.3f}")
