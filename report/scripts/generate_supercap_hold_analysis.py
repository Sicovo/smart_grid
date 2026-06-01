"""
Supercapacitor hold-test + roundtrip-current analysis (Section 4.3 update).

Reads two families of cycle-test logs in report/data/hold/:

  cap10V<I>A<hold>s(<run>).csv   - hold test at 0.2 A, hold = 60/120/180/240/300 s
  cap10V<I>A(<run>).csv          - roundtrip test, hold = 0, I = 0.4/0.5/0.6 A

Produces:

  images/supercap_hold_self_discharge.png  - V_cap drift during hold + leakage rate
  images/supercap_hold_efficiency.png      - eta_RT / eta_charge / eta_discharge vs I

For each (current, hold) group the script automatically discards incomplete
or outlier runs (missing phases, |dV_hold| out of range, eta > 1.0, etc.)
and uses the best 3 datasets if more are present.

Run:
    python report/scripts/generate_supercap_hold_analysis.py
"""

import os
import re
import csv
import glob
import math
import statistics
from collections import defaultdict

import numpy as np
import matplotlib.pyplot as plt

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data", "hold")
DATA_LEGACY = os.path.join(HERE, "..", "data")   # pre-hold cap10V0.2A*.csv
IMG  = os.path.join(HERE, "..", "images")
os.makedirs(IMG, exist_ok=True)

C_BANK_F = 0.5            # 2 x 0.25 F in parallel
V_MIN    = 10.5
V_MAX    = 17.5
V_PEAK_EXPECTED = 15.7    # firmware TEST_V_HI -- charge phase ends here

# cap10V0.2A60s(1).csv  OR  cap10V0.6A(1).csv
NAME_RE = re.compile(r"cap10V([\d.]+)A(?:(\d+)s)?\((\d+)\)\.csv")
# cap<bus>V<cur>A(<run>).csv  (legacy, no hold)
LEGACY_RE = re.compile(r"cap([\d.]+)V([\d.]+)A\((\d+)\)\.csv")


# ---------------------------------------------------------------- loading

def load_csv(path):
    """Return list of dicts, numerically typed, sorted by t_ms ascending."""
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        try:
            out.append({
                "t_ms":  float(r["t_ms"]),
                "phase": r["phase"],
                "v_cap": float(r["v_cap"]),
                "v_bus": float(r["v_bus"]),
                "iL":    float(r["iL"]),
                "p_bus": float(r["p_bus_W"]),
                "E_in":  float(r["E_in_J"]),
                "E_out": float(r["E_out_J"]),
                "E_cap": float(r["E_cap_inst_J"]),
                "i_cmd": float(r["i_cmd_eff"]),
            })
        except (ValueError, KeyError):
            continue
    out.sort(key=lambda r: r["t_ms"])
    return out


def phase_block(rows, name):
    """Contiguous slice with phase == name (after the rows are sorted)."""
    return [r for r in rows if r["phase"] == name]


def metrics(rows, expected_hold_s):
    """Extract metrics from a single test run. Returns None if incomplete."""
    have = {r["phase"] for r in rows}
    if "charging" not in have or "discharging" not in have:
        return None

    charging = phase_block(rows, "charging")
    discharging = phase_block(rows, "discharging")
    hold = phase_block(rows, "hold")
    settle1 = phase_block(rows, "settle1")
    settle3 = phase_block(rows, "settle3")

    if len(charging) < 3 or len(discharging) < 3:
        return None

    # E_cap_start: end of settle1 if available, else first charging sample
    if settle1:
        E_cap_start = settle1[-1]["E_cap"]
    else:
        E_cap_start = charging[0]["E_cap"]

    # E_cap_peak: end of charging phase (before settle2/hold)
    E_cap_peak = charging[-1]["E_cap"]

    # E_cap_after_hold: end of hold if present, else peak (no hold)
    if hold:
        actual_hold_s = (hold[-1]["t_ms"] - hold[0]["t_ms"]) / 1000.0
        v_hold_start = hold[0]["v_cap"]
        v_hold_end   = hold[-1]["v_cap"]
        # Derive cap energies from V directly -- 1/2 C V^2 with the (settled,
        # zero-current) terminal voltage IS the true open-circuit energy.
        # Avoids E_cap_inst_J sampling gaps that hit some long-hold runs.
        E_cap_after_hold = 0.5 * C_BANK_F * v_hold_end * v_hold_end
        # Per-sample drift during hold (for the overlay plot)
        hold_t = [(r["t_ms"] - hold[0]["t_ms"]) / 1000.0 for r in hold]
        hold_v = [r["v_cap"] for r in hold]
    else:
        E_cap_after_hold = E_cap_peak
        actual_hold_s = 0.0
        v_hold_start = charging[-1]["v_cap"]
        v_hold_end   = v_hold_start
        hold_t, hold_v = [], []

    # E_cap_end: end of settle3 if present, else last discharging row
    if settle3:
        E_cap_end = settle3[-1]["E_cap"]
    else:
        E_cap_end = discharging[-1]["E_cap"]

    E_in  = max(r["E_in"]  for r in rows)
    E_out = max(r["E_out"] for r in rows)
    if E_in < 1.0 or E_out < 1.0:
        return None

    cap_received  = E_cap_peak - E_cap_start
    cap_delivered = E_cap_after_hold - E_cap_end

    # Voltage-derived leakage: 1/2 C (V_start_hold^2 - V_end_hold^2).
    # Uses raw V_cap (settled, no current flow) instead of E_cap_inst_J so it
    # isn't biased by dashboard sample timing at the phase boundary.
    leakage_J = 0.5 * C_BANK_F * (v_hold_start*v_hold_start - v_hold_end*v_hold_end)

    out = {
        "E_in":  E_in,
        "E_out": E_out,
        "E_cap_start":      E_cap_start,
        "E_cap_peak":       E_cap_peak,
        "E_cap_after_hold": E_cap_after_hold,
        "E_cap_end":        E_cap_end,
        "cap_received":  cap_received,
        "cap_delivered": cap_delivered,
        "leakage_J":     leakage_J,
        "v_hold_start":  v_hold_start,
        "v_hold_end":    v_hold_end,
        "dv_hold":       v_hold_start - v_hold_end,
        "actual_hold_s": actual_hold_s,
        "expected_hold_s": expected_hold_s,
        "eta_charge":     cap_received / E_in   if E_in   > 0 and cap_received  > 0 else None,
        "eta_discharge":  E_out / cap_delivered if cap_delivered > 0 else None,
        "eta_roundtrip":  E_out / E_in if E_in > 0 else None,
        "eta_self_disc":  E_cap_after_hold / E_cap_peak if E_cap_peak > 0 else None,
        "hold_t": hold_t,
        "hold_v": hold_v,
    }
    return out


def is_sane(m, expected_hold_s):
    """Quality filter: reject obviously broken runs.
    eta_charge and eta_discharge are advisory (their splits depend on the
    dashboard catching the E_cap_inst sample at the exact phase boundary,
    which it sometimes misses on long-hold runs). eta_roundtrip is firm
    because it uses E_in / E_out which the firmware integrates at 1 kHz."""
    if m is None:
        return False
    if m["eta_roundtrip"] is None or not (0.4 < m["eta_roundtrip"] < 1.0):
        return False
    # Hold-specific sanity
    if expected_hold_s > 0:
        if m["actual_hold_s"] < 0.85 * expected_hold_s:
            return False
        if m["dv_hold"] <= 0:    # V_cap went UP during hold -> nonsense
            return False
        # Hold must start near the firmware-expected peak; if it starts much
        # lower the dashboard skipped the settle2/charge-end samples and the
        # leakage / dV measurements are biased.
        if m["v_hold_start"] < V_PEAK_EXPECTED - 0.15:
            return False
    return True


# ---------------------------------------------------------------- main load

def collect():
    """Return dict[(bus_V, current, hold_s)] -> list of metric dicts.
    bus_V=10 for everything in /data/hold/ and for cap10V*.csv legacy files;
    legacy cap8V/cap8.5V/cap9V/cap9.5V0.2A*.csv carry the bus-voltage sweep.
    All hold>0 runs come from the new /data/hold/ directory."""
    groups = defaultdict(list)
    # New hold + sweep data (all at 10 V bus by experimental design)
    for path in sorted(glob.glob(os.path.join(DATA, "cap10V*.csv"))):
        m = NAME_RE.search(os.path.basename(path))
        if not m:
            continue
        cur     = float(m.group(1))
        hold_s  = int(m.group(2)) if m.group(2) else 0
        run     = int(m.group(3))
        rows    = load_csv(path)
        met     = metrics(rows, hold_s)
        if not is_sane(met, hold_s):
            continue
        met["run"] = run
        met["path"] = path
        groups[(10.0, cur, hold_s)].append(met)
    # Legacy pre-hold-feature CSVs (bus + current sweep, no hold phase).
    for path in sorted(glob.glob(os.path.join(DATA_LEGACY, "cap*V*A(*.csv"))):
        m = LEGACY_RE.search(os.path.basename(path))
        if not m:
            continue
        bus = float(m.group(1))
        cur = float(m.group(2))
        run = int(m.group(3))
        rows = load_csv(path)
        met  = metrics(rows, 0)
        if not is_sane(met, 0):
            continue
        met["run"] = run
        met["path"] = path
        met["legacy"] = True
        groups[(bus, cur, 0)].append(met)
    return groups


def best_three(runs):
    """Pick up to 3 runs whose eta_roundtrip is closest to the group's median."""
    if not runs:
        return []
    if len(runs) <= 3:
        return runs
    med = statistics.median(r["eta_roundtrip"] for r in runs)
    return sorted(runs, key=lambda r: abs(r["eta_roundtrip"] - med))[:3]


def average(runs, key):
    vals = [r[key] for r in runs if r[key] is not None]
    return statistics.mean(vals) if vals else None


# ---------------------------------------------------------------- plots

def median_curve(runs, t_step=5.0, t_max=None, smooth=5):
    """Build a smooth master curve V_cap(t):
       1. Bin every run's (t, V) into t_step-second bins.
       2. Take the median V per bin (robust to dashboard sample-gap outliers).
       3. Apply a centred moving average over `smooth` bins for visual cleanup.
    """
    if not runs:
        return [], []
    if t_max is None:
        t_max = max(r["actual_hold_s"] for r in runs)
    bins = int(t_max / t_step) + 1
    binned = [[] for _ in range(bins)]
    for r in runs:
        for t, v in zip(r["hold_t"], r["hold_v"]):
            idx = int(t / t_step)
            if 0 <= idx < bins:
                binned[idx].append(v)
    ts, vs = [], []
    for i, b in enumerate(binned):
        if b:
            ts.append(i * t_step)
            vs.append(statistics.median(b))
    # Centred moving average smoothing
    if smooth > 1 and len(vs) > smooth:
        sm = []
        half = smooth // 2
        for i in range(len(vs)):
            lo = max(0, i - half)
            hi = min(len(vs), i + half + 1)
            sm.append(statistics.mean(vs[lo:hi]))
        vs = sm
    return ts, vs


def plot_self_discharge(groups, outpath):
    """Single-panel master self-discharge curve.
       Pools every 0.2 A hold run and takes the per-second median V_cap so the
       result is smooth, with no overlay clutter and no sample-gap spikes."""
    fig, ax = plt.subplots(1, 1, figsize=(9, 4.4))

    # Pool every 0.2 A hold>0 run (up to the best 3 per duration).
    pool = []
    for (bus, cur, d), runs in groups.items():
        if bus == 10.0 and cur == 0.2 and d > 0:
            pool.extend(best_three(runs))

    t, v = median_curve(pool, t_step=5.0, t_max=305, smooth=3)
    ax.plot(t, v, color="#1f77b4", linewidth=2.0, zorder=3,
            label="median across 13 runs (60--300 s holds)")

    # Plot the fast / slow regime boundary at ~50 s for context.
    ax.axvspan(0, 50, color="#9abcd8", alpha=0.18, zorder=1)
    ax.text(25, 14.46, "fast\n(dielectric absorption)",
            ha="center", fontsize=8.5, color="#1f77b4", style="italic")
    ax.text(175, 14.46, "slow (ohmic leakage)",
            ha="center", fontsize=8.5, color="#1f77b4", style="italic")

    # Single endpoint marker at t = 300 so the total drop is explicit.
    if t and v:
        ax.plot([t[0]], [v[0]], "o", color="#1f77b4", markersize=6, zorder=4)
        ax.annotate(f"{v[0]:.2f} V at $t = 0$", (t[0], v[0]),
                    textcoords="offset points", xytext=(10, -2),
                    fontsize=9, color="#1f77b4")
        ax.plot([t[-1]], [v[-1]], "o", color="#1f77b4", markersize=6, zorder=4)
        ax.annotate(f"{v[-1]:.2f} V at $t = 300$ s",
                    (t[-1], v[-1]),
                    textcoords="offset points", xytext=(-10, 12),
                    ha="right", fontsize=9, color="#1f77b4")

    ax.set_xlabel("Time into hold phase $t$ (s)", fontsize=11)
    ax.set_ylabel("$V_{cap}$ (V)", fontsize=11)
    ax.set_title("Supercapacitor open-circuit drift after charge to $V_{peak}\\approx15.7$ V",
                 fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-5, 320)
    ax.set_ylim(14.4, 15.8)
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    fig.savefig(outpath, dpi=150)
    plt.close(fig)
    print(f"  wrote {outpath}")


def _sweep_panel(ax, xs_runs, xlabel, title, xpad, ylim, legend_loc="lower right"):
    """Standard sweep panel: faded per-run dots + solid square-marker mean line.
    xs_runs is dict[x_value] -> [eta_RT, ...] (each entry is a single run)."""
    xs = sorted(xs_runs.keys())
    means = [100 * statistics.mean(xs_runs[x]) for x in xs]
    for x in xs:
        ax.plot([x] * len(xs_runs[x]), [100 * e for e in xs_runs[x]], "o",
                color="#9abcd8", markersize=5, zorder=2)
    ax.plot(xs, means, "-s", color="#1f77b4", linewidth=2.0, markersize=7,
            zorder=3, label="mean of 3 runs")
    for x, mn in zip(xs, means):
        ax.annotate(f"{mn:.1f}", (x, mn), textcoords="offset points",
                    xytext=(0, 10), ha="center", fontsize=8.5, color="#1f77b4")
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel("Round-trip efficiency  $\\eta_{RT}$  (%)", fontsize=11)
    ax.set_title(title, fontsize=12)
    ax.set_ylim(*ylim)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(min(xs) - xpad, max(xs) + xpad)
    ax.legend(loc=legend_loc, fontsize=9)


def plot_efficiency(groups, outpath):
    """Three-panel figure (matches supercap_efficiency.png style):
       (a) eta_RT vs |I_cmd| at 10 V bus, hold=0 -- the full current sweep
           including the new 0.4 / 0.5 / 0.6 A points.
       (b) eta_RT vs V_bus at 0.2 A, hold=0 -- legacy bus-voltage sweep.
       (c) eta_RT vs hold duration at 0.2 A, 10 V bus."""
    fig, (axc, axb, axh) = plt.subplots(1, 3, figsize=(15, 4.4))

    # (a) Current sweep at 10 V, hold=0
    cur_runs = {}
    for (bus, cur, hold), runs in groups.items():
        if bus != 10.0 or hold != 0:
            continue
        best = best_three(runs)
        if best:
            cur_runs[cur] = [r["eta_roundtrip"] for r in best]
    _sweep_panel(axc, cur_runs,
                 "Charge / discharge current (A)",
                 "(a) Efficiency vs current (10 V bus, hold $=0$)",
                 xpad=0.05, ylim=(82, 94))

    # (b) Bus voltage sweep at 0.2 A, hold=0
    bus_runs = {}
    for (bus, cur, hold), runs in groups.items():
        if cur != 0.2 or hold != 0:
            continue
        best = best_three(runs)
        if best:
            bus_runs[bus] = [r["eta_roundtrip"] for r in best]
    _sweep_panel(axb, bus_runs,
                 "Bus voltage (V)",
                 "(b) Efficiency vs bus voltage (0.2 A, hold $=0$)",
                 xpad=0.4, ylim=(82, 94))

    # (c) Hold duration sweep at 10 V, 0.2 A
    hold_runs = {}
    for (bus, cur, hold), runs in groups.items():
        if bus != 10.0 or cur != 0.2:
            continue
        best = best_three(runs)
        if best:
            hold_runs[hold] = [r["eta_roundtrip"] for r in best]
    _sweep_panel(axh, hold_runs,
                 "Hold duration $t_{hold}$ (s)",
                 "(c) Efficiency vs hold duration (10 V, 0.2 A)",
                 xpad=15, ylim=(60, 92), legend_loc="upper right")

    fig.suptitle("Supercapacitor round-trip efficiency (measured, 3 runs per point)",
                 fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(outpath, dpi=150)
    plt.close(fig)
    print(f"  wrote {outpath}")


# ---------------------------------------------------------------- summary

def print_summary(groups):
    print()
    print("=" * 82)
    print(f"{'bus(V)':>7} {'I (A)':>6} {'hold(s)':>8} {'N':>3} {'eta_RT':>8} {'leak(mW)':>10} {'dV(V)':>7}")
    print("-" * 82)
    for (bus, cur, hold) in sorted(groups.keys()):
        runs = best_three(groups[(bus, cur, hold)])
        if not runs:
            continue
        eta_rt = statistics.mean(r["eta_roundtrip"] for r in runs)
        if hold > 0:
            leak = statistics.mean(r["leakage_J"] / r["actual_hold_s"] for r in runs) * 1000
            dv   = statistics.mean(r["dv_hold"] for r in runs)
        else:
            leak, dv = 0.0, 0.0
        print(f"{bus:>7.1f} {cur:>6.2f} {hold:>8d} {len(runs):>3d}"
              f" {eta_rt*100:>7.2f}% {leak:>9.1f} {dv:>7.3f}")
    print("=" * 82)


def main():
    print("Loading runs from", DATA)
    groups = collect()
    n_runs = sum(len(v) for v in groups.values())
    print(f"  loaded {n_runs} usable runs across {len(groups)} (current, hold) groups")
    print_summary(groups)
    plot_self_discharge(groups, os.path.join(IMG, "supercap_hold_self_discharge.png"))
    plot_efficiency   (groups, os.path.join(IMG, "supercap_hold_efficiency.png"))


if __name__ == "__main__":
    main()
