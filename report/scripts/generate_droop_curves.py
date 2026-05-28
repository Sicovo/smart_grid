"""
Generates the design-illustration droop curves figure for the report.

Output: images/droop_curves.png  (saved relative to repo root)

Each module's current is plotted as a function of bus voltage. The droop
modules (Import and Export SMPS) produce sloped curves; the non-droop
modules (PV at MPPT, Supercap on command, LED Load) appear as horizontal
lines at example values that you can change at the top of this script.

This is a SPECIFICATION diagram, not measured data.

Run from the repo root:
    python scripts/generate_droop_curves.py
"""

import os
import matplotlib.pyplot as plt
import numpy as np

# ============================================================
#  Design parameters - edit as numbers firm up
# ============================================================

# Droop setpoints and dead-band
V_NOMINAL          = 10.0   # V - bus nominal
V_IMPORT_SETPOINT  = 9.9    # V - import sources when V_bus < 9.9
V_EXPORT_SETPOINT  = 10.1   # V - export sinks when V_bus > 10.1
DROOP_BAND_HALF    = 0.1    # V - half-width over which droop reaches I_max

# Rated currents at edge of droop band (PLACEHOLDERS)
I_IMPORT_MAX = 3.0          # A - max import current
I_EXPORT_MAX = 3.0          # A - max export current

# Example currents for non-droop modules (PLACEHOLDERS)
I_PV_MPPT  =  1.0           # A - PV at MPPT (sources into bus)
I_SUPERCAP =  1.5           # A - commanded supercap current (+ sourcing)
I_LED_LOAD =  1.2           # A - LED load draw (sinks from bus)

# X-axis range
V_MIN = 9.7
V_MAX = 10.3

# Output
OUT_PATH = os.path.join("images", "droop_curves.png")


# ============================================================
#  Curve generation
# ============================================================

V_bus = np.linspace(V_MIN, V_MAX, 1000)

slope_import = I_IMPORT_MAX / DROOP_BAND_HALF
slope_export = I_EXPORT_MAX / DROOP_BAND_HALF

# Import: zero above 9.9, ramps up below, saturates at I_IMPORT_MAX
I_import = np.where(
    V_bus < V_IMPORT_SETPOINT,
    np.minimum(I_IMPORT_MAX, slope_import * (V_IMPORT_SETPOINT - V_bus)),
    0.0,
)

# Export: zero below 10.1, ramps down (negative) above, saturates at -I_EXPORT_MAX
I_export = np.where(
    V_bus > V_EXPORT_SETPOINT,
    -np.minimum(I_EXPORT_MAX, slope_export * (V_bus - V_EXPORT_SETPOINT)),
    0.0,
)

# Non-droop modules: horizontal lines
I_pv  = np.full_like(V_bus,  I_PV_MPPT)
I_cap = np.full_like(V_bus,  I_SUPERCAP)
I_led = np.full_like(V_bus, -I_LED_LOAD)


# ============================================================
#  Plot
# ============================================================

fig, ax = plt.subplots(figsize=(9.0, 5.2))

# Dead-band shading
ax.axvspan(
    V_IMPORT_SETPOINT, V_EXPORT_SETPOINT,
    color="#cccccc", alpha=0.35, zorder=0, label="Dead-band",
)

# Reference lines
ax.axhline(0, color="black", linewidth=0.6, zorder=1)
ax.axvline(V_NOMINAL, color="gray", linestyle=":", linewidth=0.8, alpha=0.7, zorder=1)

# Droop curves (solid)
ax.plot(V_bus, I_import, color="#1f77b4", linewidth=2.2, label="Import SMPS (droop)")
ax.plot(V_bus, I_export, color="#d62728", linewidth=2.2, label="Export SMPS (droop)")

# Non-droop curves (dashed, example values)
ax.plot(V_bus, I_pv,  color="#2ca02c", linestyle="--", linewidth=1.6,
        label=f"PV SMPS at MPPT (example {I_PV_MPPT:g} A)")
ax.plot(V_bus, I_cap, color="#9467bd", linestyle="--", linewidth=1.6,
        label=f"Supercap commanded (example {I_SUPERCAP:+g} A)")
ax.plot(V_bus, I_led, color="#ff7f0e", linestyle="--", linewidth=1.6,
        label=f"LED Load (example {-I_LED_LOAD:+g} A)")

# Setpoint annotations
y_low = -I_EXPORT_MAX * 1.18
ax.annotate(
    "9.9 V\nimport setpoint",
    xy=(V_IMPORT_SETPOINT, 0),
    xytext=(V_IMPORT_SETPOINT, y_low),
    ha="center", fontsize=9, color="#1f77b4",
    arrowprops=dict(arrowstyle="->", color="#1f77b4", lw=0.8),
)
ax.annotate(
    "10.1 V\nexport setpoint",
    xy=(V_EXPORT_SETPOINT, 0),
    xytext=(V_EXPORT_SETPOINT, y_low),
    ha="center", fontsize=9, color="#d62728",
    arrowprops=dict(arrowstyle="->", color="#d62728", lw=0.8),
)

# Axis labels and title
ax.set_xlabel("Bus voltage $V_{bus}$ (V)", fontsize=12)
ax.set_ylabel("Module current (A)\n(+ source into bus,   - sink from bus)", fontsize=11)
ax.set_title("Droop coordination: per-module current vs bus voltage", fontsize=13)

# Grid, legend, limits
ax.grid(True, alpha=0.3)
ax.legend(loc="upper right", fontsize=9, framealpha=0.95)
ax.set_xlim(V_MIN, V_MAX)
ax.set_ylim(-I_EXPORT_MAX * 1.4, I_IMPORT_MAX * 1.25)

plt.tight_layout()

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
plt.savefig(OUT_PATH, dpi=200, bbox_inches="tight")
print(f"Saved {OUT_PATH}")
