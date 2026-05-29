"""
Supercapacitor cycle-test results (Section 4.3).

Reads the measured cycle-test logs in report/data/ (one CSV per run, named
cap<bus>V<current>A(<run>).csv) and produces:

  images/supercap_cycle_trace.png  - one representative charge/discharge cycle
  images/supercap_efficiency.png   - round-trip efficiency vs current and vs bus voltage

Round-trip efficiency is taken as eta_RT = E_out / E_in, both bus-side energies
integrated at 1 kHz in firmware. This avoids the cap-side OCV split (eta_charge /
eta_discharge), which the data shows is confounded by the supercapacitor's charge
redistribution (the discharge OCV split can exceed 100%).

Run:
    python scripts/generate_supercap_results.py
"""

import os
import re
import csv
import glob
import numpy as np
import matplotlib.pyplot as plt

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data")
IMG  = os.path.join(HERE, "..", "images")

NAME_RE = re.compile(r"cap([\d.]+)V([\d.]+)A\((\d)\)")


def load():
    runs = []
    for path in sorted(glob.glob(os.path.join(DATA, "cap*.csv"))):
        m = NAME_RE.search(os.path.basename(path))
        if not m:
            continue
        bus, cur, run = float(m.group(1)), float(m.group(2)), int(m.group(3))
        with open(path, newline="") as f:
            rows = [r for r in csv.DictReader(f)]
        def col(key):
            return np.array([float(r[key]) for r in rows])
        E_in  = col("E_in_J").max()
        E_out = col("E_out_J").max()
        runs.append({
            "bus": bus, "cur": cur, "run": run,
            "E_in": E_in, "E_out": E_out, "eta": E_out / E_in,
            "rows": rows,
        })
    return runs


def grouped(runs, fixed_key, fixed_val, var_key):
    """Return {var_val: [eta, ...]} for runs where fixed_key == fixed_val."""
    out = {}
    for r in runs:
        if abs(r[fixed_key] - fixed_val) < 1e-6:
            out.setdefault(r[var_key], []).append(r["eta"])
    return dict(sorted(out.items()))


runs = load()

# ---- console summary ----
print(f"{'bus':>5} {'I':>5} {'run':>3} {'E_in':>7} {'E_out':>7} {'eta_RT':>7}")
for r in sorted(runs, key=lambda x: (x["bus"], x["cur"], x["run"])):
    print(f"{r['bus']:5.1f} {r['cur']:5.2f} {r['run']:3d} "
          f"{r['E_in']:7.2f} {r['E_out']:7.2f} {100*r['eta']:6.1f}%")

cur_sweep = grouped(runs, "bus", 10.0, "cur")     # at 10 V
bus_sweep = grouped(runs, "cur", 0.2, "bus")      # at 0.2 A
print("\ncurrent sweep (10 V):", {k: round(100*np.mean(v), 1) for k, v in cur_sweep.items()})
print("bus sweep (0.2 A):    ", {k: round(100*np.mean(v), 1) for k, v in bus_sweep.items()})


# ============================================================
#  Figure 1: representative cycle trace (10 V bus, 0.2 A)
# ============================================================

trace = next(r for r in runs if r["bus"] == 10.0 and r["cur"] == 0.2 and r["run"] == 1)
rows = sorted(trace["rows"], key=lambda r: int(r["t_ms"]))
t   = np.array([int(r["t_ms"]) for r in rows]) / 1000.0
vc  = np.array([float(r["v_cap"]) for r in rows])
ein = np.array([float(r["E_in_J"]) for r in rows])
eout = np.array([float(r["E_out_J"]) for r in rows])
ph  = [r["phase"] for r in rows]

def span(phase):
    ts = [t[i] for i, p in enumerate(ph) if p == phase]
    return (min(ts), max(ts)) if ts else None

fig, ax = plt.subplots(figsize=(10.0, 5.0))
for phase, color, label in [("charging", "#cfe0f3", "charge"),
                            ("discharging", "#f3d2cf", "discharge")]:
    s = span(phase)
    if s:
        ax.axvspan(s[0], s[1], color=color, alpha=0.7, zorder=0, label=label)

ax.plot(t, vc, color="#1f77b4", linewidth=2.0, label="$V_{cap}$")
ax.set_xlabel("Time (s)", fontsize=12)
ax.set_ylabel("Capacitor voltage  $V_{cap}$  (V)", color="#1f77b4", fontsize=12)
ax.tick_params(axis="y", labelcolor="#1f77b4")
ax.set_ylim(10, 16.5)
ax.grid(True, alpha=0.3)

ax2 = ax.twinx()
ax2.plot(t, ein,  color="#2ca02c", linewidth=1.8, label="$E_{in}$ (bus)")
ax2.plot(t, eout, color="#d62728", linewidth=1.8, label="$E_{out}$ (bus)")
ax2.set_ylabel("Energy  (J)", fontsize=12)
ax2.set_ylim(0, 45)

h1, l1 = ax.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="center right", fontsize=9, framealpha=0.95)
ax.set_title(f"Supercapacitor cycle test (10 V bus, 0.2 A), "
             f"$E_{{in}}$ = {trace['E_in']:.1f} J, $E_{{out}}$ = {trace['E_out']:.1f} J, "
             f"$\\eta_{{RT}}$ = {100*trace['eta']:.0f}%", fontsize=12)

plt.tight_layout()
os.makedirs(IMG, exist_ok=True)
out1 = os.path.join(IMG, "supercap_cycle_trace.png")
plt.savefig(out1, dpi=200, bbox_inches="tight")
print("\nSaved", os.path.normpath(out1))
plt.close(fig)


# ============================================================
#  Figure 2: efficiency vs current and vs bus voltage
# ============================================================

fig, (axc, axb) = plt.subplots(1, 2, figsize=(11.0, 4.5))

def plot_sweep(ax, sweep, xlabel, title, xpad):
    xs = sorted(sweep.keys())
    means = [100 * np.mean(sweep[x]) for x in xs]
    for x in xs:
        ax.plot([x] * len(sweep[x]), [100 * e for e in sweep[x]], "o",
                color="#9abcd8", markersize=5, zorder=2)
    ax.plot(xs, means, "-s", color="#1f77b4", linewidth=2.0, markersize=7,
            zorder=3, label="mean of 3 runs")
    for x, mn in zip(xs, means):
        ax.annotate(f"{mn:.1f}", (x, mn), textcoords="offset points",
                    xytext=(0, 10), ha="center", fontsize=8.5, color="#1f77b4")
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel("Round-trip efficiency  $\\eta_{RT}$  (%)", fontsize=11)
    ax.set_title(title, fontsize=12)
    ax.set_ylim(82, 94)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(min(xs) - xpad, max(xs) + xpad)
    ax.legend(loc="lower right", fontsize=9)

plot_sweep(axc, cur_sweep, "Charge / discharge current (A)",
           "Efficiency vs current (10 V bus)", 0.05)
plot_sweep(axb, bus_sweep, "Bus voltage (V)",
           "Efficiency vs bus voltage (0.2 A)", 0.4)

fig.suptitle("Supercapacitor round-trip efficiency (measured, 3 runs per point)", fontsize=13)
plt.tight_layout(rect=[0, 0, 1, 0.96])
out2 = os.path.join(IMG, "supercap_efficiency.png")
plt.savefig(out2, dpi=175, bbox_inches="tight")
print("Saved", os.path.normpath(out2))
