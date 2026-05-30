"""
Measured PV SMPS conversion efficiency vs bus voltage (Section 3.3.3).

At 100% irradiance with the panel pinned at its MPP (V_panel ~ 6.23 V,
P_panel ~ 2.3 W), the bus voltage was swept across seven points from 7.1 V to
10.2 V in 0.5 V steps. The corresponding boost duty cycle (D = 1 - V_panel /
V_bus) varies from 0.13 to 0.39 across the sweep.

Saves to:  images/pv_efficiency_measured.png   (this script does NOT touch
images/pv_efficiency.png, which is the external Navamani et al. 2015 figure
referenced for comparison in the report.)

Run:
    python scripts/generate_pv_efficiency_measured.py
"""

import os
import numpy as np
import matplotlib.pyplot as plt

HERE = os.path.dirname(__file__)
IMG  = os.path.join(HERE, "..", "images")

# (V_bus, V_panel, D, P_panel_W, P_bus_W, eta)
DATA = [
    ( 7.11, 6.22, 0.13, 2.42, 2.30, 0.950),
    ( 7.61, 6.23, 0.18, 2.34, 2.25, 0.962),
    ( 8.11, 6.23, 0.23, 2.25, 2.19, 0.973),
    ( 8.61, 6.23, 0.28, 2.28, 2.25, 0.987),
    ( 9.12, 6.23, 0.32, 2.30, 2.26, 0.983),
    ( 9.61, 6.23, 0.35, 2.45, 2.40, 0.980),
    (10.21, 6.23, 0.39, 2.26, 2.21, 0.978),
]

V_BUS = np.array([r[0] for r in DATA])
ETA   = np.array([100 * r[5] for r in DATA])

fig, ax = plt.subplots(figsize=(8.0, 4.4))

# measured trace
ax.plot(V_BUS, ETA, "-o", color="#1f77b4", markersize=8, linewidth=1.6,
        markerfacecolor="#1f77b4", markeredgecolor="white",
        zorder=3, label="measured (100% irradiance)")

# mean reference line
mean_eta = ETA.mean()
ax.axhline(mean_eta, color="#1f77b4", linewidth=0.9, linestyle=":", alpha=0.65, zorder=1,
           label=f"mean {mean_eta:.1f}%")

# annotate each point with its measured efficiency
for v, e in zip(V_BUS, ETA):
    ax.annotate(f"{e:.1f}%", (v, e), textcoords="offset points",
                xytext=(0, 11), ha="center", fontsize=8.8, color="#1f3d6f")

ax.set_xlim(6.8, 10.6)
ax.set_ylim(92, 102)
ax.set_xlabel(r"Bus voltage  $V_{\mathrm{bus}}$  (V)", fontsize=11)
ax.set_ylabel(r"Conversion efficiency  $\eta_{\mathrm{PV}}$  (%)", fontsize=11)
ax.set_title("Measured PV SMPS efficiency vs bus voltage "
             r"(100% irradiance, $V_{\mathrm{panel}} \approx 6.23$ V, "
             r"$P_{\mathrm{panel}} \approx 2.3$ W)",
             fontsize=11)
ax.grid(True, alpha=0.3)
ax.legend(loc="lower right", fontsize=9.5, framealpha=0.95)

plt.tight_layout()
os.makedirs(IMG, exist_ok=True)
out = os.path.join(IMG, "pv_efficiency_measured.png")
plt.savefig(out, dpi=180, bbox_inches="tight")
print(f"Mean eta = {mean_eta:.2f}%, std = {ETA.std(ddof=1):.2f}%, "
      f"range = {ETA.min():.1f}-{ETA.max():.1f}%")
print("Saved", os.path.normpath(out))
