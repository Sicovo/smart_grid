# cap_smps.py — Supercapacitor bidirectional SMPS, command-driven current source/sink.
#
# Hardware: Bidirectional Buck/Boost SMPS Module.
#   Switches: BU/BO -> BOOST,  OL/CL -> CL,  HMOS + LMOS both ON.
#   Port A = supercap (10.5–17.5 V),  Port B = bus (10 V nominal).
#
#   BU/BO=BOOST is chosen so the Pico is powered from Port B (bus) — the board
#   boots even when the cap is empty. PWM polarity matches pv_smps.py
#   (no `65536 - pwm_out` inversion).
#
# Energy storage: 2 × 0.25 F bank in parallel (0.5 F total), 18 V rating.
#   SMPS hardware current limit: 0.76 A. We clamp |i_cmd| at 0.60 A,
#   leaving ~21% headroom under the hardware limit.
#   Usable window 10.5 V (below this Va<Vb, SMPS can't transfer) to 17.5 V
#   (SMPS port limit, under cap rating). ~49 J of usable energy in that window.
#
# Control architecture: no outer bus-voltage loop — grid/export handle bus
# regulation. The cap is a *commanded* current source/sink. The "outer" is
# just three safety clamps on i_cmd:
#   1. |i_cmd| clamped to I_CAP_MAX (0.60 A).
#   2. Linear taper to 0 as V_cap approaches its ceiling (over 17.0 -> 17.5 V).
#   3. Linear taper to 0 as V_cap approaches its floor   (over 11.0 -> 10.5 V).
# The inner loop is a single PI current controller, exactly like pv_smps's
# inner loop — only difference is that i_cmd can be negative.
#
# Sign convention (matches pv_smps INA negation):
#   iL > 0  =>  current B->A  =>  charging cap   (bus  -> cap)
#   iL < 0  =>  current A->B  =>  discharging cap (cap -> bus)
#   i_cmd > 0 charges, i_cmd < 0 discharges.
#
# Telemetry: { role, v_cap, vb_bus, iL, p_cap, p_avg3s, soc_pct, energy_J,
#              i_cmd, i_cmd_eff, pwm, trip, trip_reason, enable, wd,
#              -- cycle-test fields (meaningful while test_phase != 'idle') --
#              test_phase, test_t_ms,
#              test_i_charge_set, test_i_discharge_set,
#              test_E_in_J, test_E_out_J,
#              test_E_cap_start_J, test_E_cap_peak_J, test_E_cap_end_J,
#              test_eta_charge, test_eta_discharge, test_eta_roundtrip }
# Commands:  { enable, i_cmd, reset_trip,
#              -- cycle-test (efficiency characterisation) --
#              test_start, test_abort, test_i_charge, test_i_discharge }
#
# Noise treatment (matches pv_smps):
#   - 16-sample INA219 averaging
#   - 4x ADC oversample on va, vb reads
#   - EMA on va, vb, iL with alpha=0.05 (~20 ms tau) feeds the telemetry
#     display so dashboard sees calm signals. Inner PI + safety still
#     use the raw single-sample values for fast response.
#   - p_cap = vb_lp * iL_lp -- the bus-side V*I product. Positive when
#     charging (= bus-input Pin, pre-loss). Negative when discharging
#     (magnitude = bus-output Pout, post-loss). NOT a cap-side power.
#   - p_avg3s = true 3-second block average of p_cap; window restarts
#     on i_cmd / enable / test-phase change so steady-state numbers
#     are comparable across operating points.
#
# Cycle test: triggered by `test_start: 1`. Runs precharge -> settle ->
# charge -> settle -> discharge -> settle between V_TEST_LO and V_TEST_HI
# at the user-supplied charge / discharge currents (default 0.2 A each).
# Integrates bus-side E_in over the charge phase and E_out over the
# discharge phase at the full 1 kHz tick rate; captures cap-side
# (1/2) C V^2 at each settle (open-circuit, ESR-free). On completion
# exposes eta_charge / eta_discharge / eta_roundtrip and returns to
# normal command mode, armed for the next run. Any trip, disable, or
# `test_abort: 1` mid-test sets phase to 'aborted' and freezes the
# partial numbers.

import time
from machine import Pin, ADC, I2C, PWM, Timer, idle
from common import wifi_connect, start_http_thread

# ---------------- Hardware ----------------

va_pin = ADC(Pin(28))      # Port A = supercap
vb_pin = ADC(Pin(26))      # Port B = bus
pwm    = PWM(Pin(9))
pwm.freq(100_000)
i2c    = I2C(0, scl=Pin(1), sda=Pin(0), freq=2_400_000)
ADDR, SHUNT = 0x40, 0.10

def ina_init():
    # Was 0x1DDF (8-sample averaging). Bumped to 0x1E67 -> 16-sample,
    # ~8.5 ms conversion. Matches pv_smps. Sits inside the 3 s averaging
    # window comfortably and visibly quietens iL.
    i2c.writeto_mem(ADDR, 0x00, b'\x1E\x67')
    i2c.writeto_mem(ADDR, 0x05, b'\x00\x00')

def ina_current():
    # Shunt wired A->B (buck-positive); BOOST flows B->A so negate.
    # Result: positive iL = charging the cap (bus -> cap, B -> A).
    raw = i2c.readfrom_mem(ADDR, 0x01, 2)
    v = int.from_bytes(raw, 'big')
    if v > 32767:
        v -= 65536
    return -(v * 1e-5) / SHUNT

def read_va():
    # 4x oversample -- Pico ADC LSB noise is the dominant noise source.
    # ~10 us overhead inside a 1 ms tick budget.
    s = va_pin.read_u16() + va_pin.read_u16() + va_pin.read_u16() + va_pin.read_u16()
    return 1.017 * (12490/2490) * 3.3 * (s >> 2) / 65536

def read_vb():
    s = vb_pin.read_u16() + vb_pin.read_u16() + vb_pin.read_u16() + vb_pin.read_u16()
    return 1.015 * (12490/2490) * 3.3 * (s >> 2) / 65536

def sat(x, hi, lo):
    return max(lo, min(hi, x))

# ---------------- Tuning ----------------

# Supercap voltage limits — datasheet rating is 18 V, SMPS port maxes at 17.5 V,
# and Va > Vb is required for the SMPS to transfer power, so the lower edge
# sits a hair above the bus voltage.
V_CAP_MAX       = 17.5    # hard ceiling (SMPS port limit, comfortably under 18 V cap rating)
V_CAP_MIN       = 10.5    # hard floor   (Va > Vbus margin)
V_CAP_TAPER_HI  = 17.0    # start tapering charge current here, fully zero at V_CAP_MAX
V_CAP_TAPER_LO  = 11.0    # start tapering discharge current here, fully zero at V_CAP_MIN

# Current command limit — ~21% headroom under the 0.76 A SMPS hardware limit.
I_CAP_MAX       = 0.60

# Inner current loop gains — same shape as pv_smps inner loop. Tune after bring-up.
KP_I, KI_I      = 100, 200

# PWM range — same as pv_smps (BOOST, no inversion).
PWM_MIN         = 0
PWM_MAX         = 45000

# Anti-windup integrator bound.
I_ERR_INT_LIMIT = 500.0

# Safety trips (all non-latching except cap overvolt).
V_CAP_OVERVOLT  = 17.8    # belt-and-braces — taper should keep us under 17.5
VB_CRASH        = 2.0     # bus collapsed — refuse to operate
VB_OVERVOLT     = 13.0    # bus runaway — refuse to operate
I_TRIP_ABS      = 0.70    # ~17% over the 0.60 A cap, ~8% under the 0.76 A hardware limit

# Bus-droop awareness — back off charging if the bus is sagging, so cap_smps
# doesn't fight grid_smps for current and trigger a runaway. Linear taper:
# full i_cmd at VB_HEALTHY, zero at VB_BACKOFF.
VB_NOMINAL      = 10.0
VB_HEALTHY      = 9.5
VB_BACKOFF      = 8.5

# Hard charge cutoff — when Vcap reaches this, force i_cmd_eff to 0 regardless
# of the dashboard command. Set well below the SMPS hardware misbehavior zone
# (~16 V) so we never reach the runaway region during charging.
V_CAP_CHARGE_CUTOFF = 15.7

# ---------------- Cycle-test tuning ----------------
# Endpoints: full operating window (10.5 -> 15.7 V). TEST_V_HI matches
# V_CAP_CHARGE_CUTOFF so the charge phase exits at the same threshold
# the safety cutoff would have zeroed i_cmd_eff at anyway.
TEST_V_LO              = 10.5
TEST_V_HI              = 15.7
TEST_SETTLE_MS         = 500       # zero-current pause between phases
TEST_OCV_AVG_TAIL_MS   = 200       # average Vcap over this much of the settle tail
TEST_PHASE_TIMEOUT_MS  = 60000     # any single phase longer than this -> abort
TEST_I_DEFAULT         = 0.20
TEST_I_MIN             = 0.05
TEST_I_MAX             = I_CAP_MAX  # hard clamp = cap's own current limit
DT_S                   = 0.001     # tick period in seconds (for energy integration)

# ---------------- Shared state (dashboard-compatible) ----------------

state = {
    'cmd':         {'enable': 1, 'i_cmd': 0.0},
    'tlm':         {},
    'last_cmd_ms': time.ticks_ms(),
}

# ---------------- Control state ----------------

_i_err_int   = 0.0
_pwm_out     = PWM_MIN
_print_cnt   = 0
_tlm_cnt     = 0
_last_e_ms   = time.ticks_ms()   # for measured-dt energy integration
_trip_active = 0
_trip_reason = ''

# Display power filter (kept OUT of inner PI + safety guards so the
# original tuning is unchanged). Feeds telemetry display + 3 s avg.
EMA_ALPHA = 0.05
_va_lp = 0.0
_vb_lp = 0.0
_il_lp = 0.0
_p_lp  = 0.0

# 3-second block average of p_cap. Window restarts when the commanded
# operating point changes (i_cmd or enable) so each completed average
# reflects a single steady-state operating point -- this is what you
# read off the dashboard when sweeping operating points for an
# efficiency characterisation.
P_AVG_WINDOW_MS = 3000
_pavg_sum   = 0.0
_pavg_n     = 0
_pavg_start = 0
_p_avg3s    = 0.0
_prev_op    = None     # (round(i_cmd, 3), int(enabled), test_phase)

# ---- Cycle-test state ----
# Phases: 'idle' -> 'precharge' -> 'settle1' -> 'charging' -> 'settle2'
#         -> 'discharging' -> 'settle3' -> 'done' (or 'aborted' anytime).
_test_phase           = 'idle'
_test_phase_start     = 0      # ticks_ms at entry to current phase
_test_t_start         = 0      # ticks_ms at start of whole test
_test_i_charge        = TEST_I_DEFAULT
_test_i_discharge     = TEST_I_DEFAULT
_test_E_in            = 0.0    # bus-side energy in over the charge phase
_test_E_out           = 0.0    # bus-side energy out over the discharge phase
_test_E_cap_start     = 0.0    # (1/2) C V^2 captured at end of settle1
_test_E_cap_peak      = 0.0    # (1/2) C V^2 captured at end of settle2
_test_E_cap_end       = 0.0    # (1/2) C V^2 captured at end of settle3
_test_eta_charge      = 0.0
_test_eta_discharge   = 0.0
_test_eta_roundtrip   = 0.0
_test_settle_sum      = 0.0    # OCV averaging accumulator
_test_settle_n        = 0

def _test_reset():
    """Zero all cycle-test accumulators and results. Phase becomes 'idle'."""
    global _test_phase, _test_E_in, _test_E_out
    global _test_E_cap_start, _test_E_cap_peak, _test_E_cap_end
    global _test_eta_charge, _test_eta_discharge, _test_eta_roundtrip
    global _test_settle_sum, _test_settle_n
    _test_phase = 'idle'
    _test_E_in = 0.0
    _test_E_out = 0.0
    _test_E_cap_start = 0.0
    _test_E_cap_peak = 0.0
    _test_E_cap_end = 0.0
    _test_eta_charge = 0.0
    _test_eta_discharge = 0.0
    _test_eta_roundtrip = 0.0
    _test_settle_sum = 0.0
    _test_settle_n = 0

def _test_begin(i_charge, i_discharge, v_cap_now):
    """Start a new cycle test. Skips precharge if Vcap already at the floor."""
    global _test_phase, _test_phase_start, _test_t_start
    global _test_i_charge, _test_i_discharge
    _test_reset()
    _test_i_charge    = max(TEST_I_MIN, min(TEST_I_MAX, float(i_charge)))
    _test_i_discharge = max(TEST_I_MIN, min(TEST_I_MAX, float(i_discharge)))
    _test_t_start     = time.ticks_ms()
    _test_phase_start = _test_t_start
    if v_cap_now > TEST_V_LO + 0.10:
        _test_phase = 'precharge'
    else:
        _test_phase = 'settle1'

def _test_mark_aborted():
    """Force the test out of any active phase. No-op if idle / done / aborted."""
    global _test_phase
    if _test_phase not in ('idle', 'done', 'aborted'):
        _test_phase = 'aborted'

def _test_finalize_eta():
    """Compute and store the three efficiencies from accumulated energies."""
    global _test_eta_charge, _test_eta_discharge, _test_eta_roundtrip
    cap_received  = _test_E_cap_peak - _test_E_cap_start
    cap_delivered = _test_E_cap_peak - _test_E_cap_end
    _test_eta_charge    = (cap_received  / _test_E_in) if _test_E_in   > 1e-6 else 0.0
    _test_eta_discharge = (_test_E_out / cap_delivered) if cap_delivered > 1e-6 else 0.0
    _test_eta_roundtrip = (_test_E_out / _test_E_in)   if _test_E_in   > 1e-6 else 0.0

def _reset_controllers():
    global _i_err_int, _pwm_out
    _i_err_int = 0.0
    _pwm_out   = PWM_MIN

# ---------------- Soft taper + SoC helpers ----------------

def apply_soft_taper(i_cmd_raw, v_cap):
    """Clamp i_cmd to ±I_CAP_MAX, then taper toward 0 near V_cap limits.
       Charging (+) tapers between V_CAP_TAPER_HI and V_CAP_MAX.
       Discharging (−) tapers between V_CAP_TAPER_LO and V_CAP_MIN."""
    i = sat(i_cmd_raw, I_CAP_MAX, -I_CAP_MAX)
    if i > 0 and v_cap > V_CAP_TAPER_HI:
        scale = (V_CAP_MAX - v_cap) / (V_CAP_MAX - V_CAP_TAPER_HI)
        if scale < 0.0: scale = 0.0
        i = i * scale
    elif i < 0 and v_cap < V_CAP_TAPER_LO:
        scale = (v_cap - V_CAP_MIN) / (V_CAP_TAPER_LO - V_CAP_MIN)
        if scale < 0.0: scale = 0.0
        i = i * scale
    return i

# Bank capacitance: 2 × 0.25 F in parallel.
C_BANK_F = 0.5

def soc_pct(v_cap):
    """0 % at V_CAP_MIN, 100 % at V_CAP_MAX, energy-weighted (E = ½CV²)."""
    v = max(V_CAP_MIN, min(V_CAP_MAX, v_cap))
    return 100.0 * (v*v - V_CAP_MIN*V_CAP_MIN) / (V_CAP_MAX*V_CAP_MAX - V_CAP_MIN*V_CAP_MIN)

def energy_J(v_cap):
    return 0.5 * C_BANK_F * v_cap * v_cap

# ---------------- Timer flag ----------------
# Same pattern as pv_smps — timer sets a flag, the control runs in the main
# loop so Ctrl+C breaks instantly.

timer_elapsed = 0
def tick(_t):
    global timer_elapsed
    timer_elapsed = 1

# ---------------- Boot ----------------

print("Cap SMPS booting...")
ina_init()
pwm.duty_u16(PWM_MIN)
wlan = wifi_connect("cap")
print("Local IPv4:", wlan.ifconfig()[0] if wlan.isconnected() else "NOT CONNECTED")
start_http_thread(state)

loop_timer = Timer(mode=Timer.PERIODIC, freq=1000, callback=tick)
print("[cap] running. Ctrl+C to stop.")

# ---------------- Main loop ----------------

try:
    while True:
        if timer_elapsed:
            timer_elapsed = 0

            # Measured elapsed time since the last processed tick. The energy
            # integrators use this instead of a fixed 1 ms so E_in / E_out stay
            # correct even if the loop ever falls behind 1 kHz. (A stalled loop
            # used to credit 1 ms per iteration over longer real gaps, which
            # undercounted the energies and gave impossible >100% efficiencies.)
            _now_e = time.ticks_ms()
            _dt_s  = time.ticks_diff(_now_e, _last_e_ms) / 1000.0
            if _dt_s > 0.5:
                _dt_s = 0.5          # clamp pathological gaps
            _last_e_ms = _now_e

            _va = read_va()       # cap
            _vb = read_vb()       # bus
            _il = ina_current()   # +ve = charging

            # EMA filter for telemetry display + 3 s avg input.
            # Kick filters with first sample to skip the boot transient.
            if _va_lp == 0.0:
                _va_lp = _va
                _vb_lp = _vb
                _il_lp = _il
            else:
                _va_lp = (1.0 - EMA_ALPHA) * _va_lp + EMA_ALPHA * _va
                _vb_lp = (1.0 - EMA_ALPHA) * _vb_lp + EMA_ALPHA * _vb
                _il_lp = (1.0 - EMA_ALPHA) * _il_lp + EMA_ALPHA * _il
            # Bus-side V*I. Positive while charging (= Pin from bus, pre-loss);
            # negative while discharging (magnitude = Pout to bus, post-loss).
            _p_lp = _vb_lp * _il_lp

            cmd       = state['cmd']
            enabled   = bool(cmd.get('enable', 1))
            i_cmd_raw = float(cmd.get('i_cmd', 0.0))

            # 3-second block average -- restarts on operating-point change.
            # Includes test_phase so the window resets on each phase boundary
            # during a cycle test (where i_cmd_raw stays at the user's last
            # commanded value but i_cmd_eff is owned by the test machine).
            now_ms_pavg = time.ticks_ms()
            op_point    = (round(i_cmd_raw, 3), 1 if enabled else 0, _test_phase)
            if op_point != _prev_op:
                _pavg_sum   = 0.0
                _pavg_n     = 0
                _pavg_start = now_ms_pavg
                _prev_op    = op_point
            _pavg_sum += _p_lp
            _pavg_n   += 1
            if time.ticks_diff(now_ms_pavg, _pavg_start) >= P_AVG_WINDOW_MS:
                _p_avg3s    = _pavg_sum / _pavg_n
                _pavg_sum   = 0.0
                _pavg_n     = 0
                _pavg_start = now_ms_pavg

            # Dashboard reset button — clear trip + integrator + abort any
            # in-progress cycle test (the cap may have ended up in a weird
            # state and the test data is no longer trustworthy).
            if cmd.get('reset_trip', 0):
                cmd['reset_trip'] = 0
                _trip_active = 0
                _trip_reason = ''
                _reset_controllers()
                _test_mark_aborted()

            # Cycle-test commands (one-shot consume; payload values are
            # latched into the test state at start). Also zeros the user's
            # i_cmd so the cap idles cleanly after the test completes
            # rather than resuming whatever command was active before.
            if cmd.get('test_start', 0):
                cmd['test_start'] = 0
                cmd['i_cmd']      = 0.0
                _test_begin(cmd.get('test_i_charge', TEST_I_DEFAULT),
                            cmd.get('test_i_discharge', TEST_I_DEFAULT),
                            _va_lp)
                i_cmd_raw = 0.0   # apply within THIS tick too
            if cmd.get('test_abort', 0):
                cmd['test_abort'] = 0
                _test_mark_aborted()

            # ---- Cycle-test state machine ----
            # While a test is running (phase not in {idle, done, aborted}),
            # the machine sets test_i_cmd and test_override=True. Each
            # 'settle' phase pauses at zero current for TEST_SETTLE_MS and
            # captures an open-circuit Vcap averaged over the last
            # TEST_OCV_AVG_TAIL_MS (skipping the early ESR relaxation).
            test_override = False
            test_i_cmd    = 0.0
            if _test_phase not in ('idle', 'done', 'aborted'):
                now_ms_t      = time.ticks_ms()
                phase_elapsed = time.ticks_diff(now_ms_t, _test_phase_start)

                if phase_elapsed > TEST_PHASE_TIMEOUT_MS:
                    # Defensive: a phase exceeding the timeout means
                    # something is wrong (PSU current limit, panel blocking
                    # discharge, etc). Abort rather than burn forever.
                    _test_mark_aborted()
                else:
                    test_override = True
                    if _test_phase == 'precharge':
                        test_i_cmd = -_test_i_discharge
                        if _va_lp <= TEST_V_LO:
                            _test_phase       = 'settle1'
                            _test_phase_start = now_ms_t
                            _test_settle_sum  = 0.0
                            _test_settle_n    = 0
                    elif _test_phase == 'settle1':
                        test_i_cmd = 0.0
                        if phase_elapsed > TEST_SETTLE_MS - TEST_OCV_AVG_TAIL_MS:
                            _test_settle_sum += _va_lp
                            _test_settle_n   += 1
                        if phase_elapsed >= TEST_SETTLE_MS:
                            v_ocv = (_test_settle_sum / _test_settle_n) if _test_settle_n else _va_lp
                            _test_E_cap_start = 0.5 * C_BANK_F * v_ocv * v_ocv
                            _test_phase       = 'charging'
                            _test_phase_start = now_ms_t
                    elif _test_phase == 'charging':
                        test_i_cmd = +_test_i_charge
                        # Bus-side input energy. _p_lp = vb_lp * iL_lp; iL > 0
                        # during charging so _p_lp > 0.
                        _test_E_in += _p_lp * _dt_s
                        if _va_lp >= TEST_V_HI:
                            _test_phase       = 'settle2'
                            _test_phase_start = now_ms_t
                            _test_settle_sum  = 0.0
                            _test_settle_n    = 0
                    elif _test_phase == 'settle2':
                        test_i_cmd = 0.0
                        if phase_elapsed > TEST_SETTLE_MS - TEST_OCV_AVG_TAIL_MS:
                            _test_settle_sum += _va_lp
                            _test_settle_n   += 1
                        if phase_elapsed >= TEST_SETTLE_MS:
                            v_ocv = (_test_settle_sum / _test_settle_n) if _test_settle_n else _va_lp
                            _test_E_cap_peak  = 0.5 * C_BANK_F * v_ocv * v_ocv
                            _test_phase       = 'discharging'
                            _test_phase_start = now_ms_t
                    elif _test_phase == 'discharging':
                        test_i_cmd = -_test_i_discharge
                        # Bus-side output energy. iL < 0 during discharging
                        # so _p_lp < 0; magnitude is the post-loss bus power.
                        _test_E_out += (-_p_lp) * _dt_s
                        if _va_lp <= TEST_V_LO:
                            _test_phase       = 'settle3'
                            _test_phase_start = now_ms_t
                            _test_settle_sum  = 0.0
                            _test_settle_n    = 0
                    elif _test_phase == 'settle3':
                        test_i_cmd = 0.0
                        if phase_elapsed > TEST_SETTLE_MS - TEST_OCV_AVG_TAIL_MS:
                            _test_settle_sum += _va_lp
                            _test_settle_n   += 1
                        if phase_elapsed >= TEST_SETTLE_MS:
                            v_ocv = (_test_settle_sum / _test_settle_n) if _test_settle_n else _va_lp
                            _test_E_cap_end = 0.5 * C_BANK_F * v_ocv * v_ocv
                            _test_finalize_eta()
                            _test_phase   = 'done'
                            test_override = False

                # Trip or disable mid-test -> abort and release override.
                if not enabled or _trip_active:
                    _test_mark_aborted()
                    test_override = False

            # ---- i_cmd_eff resolution ----
            if test_override:
                # Test owns i_cmd. Skip soft taper / V_CAP_CHARGE_CUTOFF /
                # bus-droop scaling -- the test's own endpoints handle all
                # of those concerns deterministically. ±I_CAP_MAX hard
                # clamp remains as a final safety.
                i_cmd_eff = sat(test_i_cmd, I_CAP_MAX, -I_CAP_MAX) if enabled else 0.0
            else:
                # Normal user-driven path.
                # Apply soft taper + ±I_CAP_MAX clamp. Disabled => 0.
                i_cmd_eff = apply_soft_taper(i_cmd_raw, _va) if enabled else 0.0

                # Hard charge cutoff at V_CAP_CHARGE_CUTOFF.
                if i_cmd_eff > 0.0 and _va >= V_CAP_CHARGE_CUTOFF:
                    i_cmd_eff = 0.0

                # Bus-droop awareness: scale charging command down if bus is
                # sagging. Cap_smps shares port B with grid_smps + loadbank;
                # if we keep demanding full charge current while the bus
                # droops we hit a positive-feedback collapse. Scaling charge
                # demand by bus health breaks that loop. Charging only --
                # discharging into a sagging bus actually helps.
                if i_cmd_eff > 0.0:
                    vb_scale = (_vb - VB_BACKOFF) / (VB_HEALTHY - VB_BACKOFF)
                    if vb_scale < 0.0: vb_scale = 0.0
                    elif vb_scale > 1.0: vb_scale = 1.0
                    i_cmd_eff = i_cmd_eff * vb_scale

            # ---- Telemetry (throttled to ~50 Hz) ----
            # v_cap, vb_bus, iL, p_cap are EMA-filtered for calm dashboard
            # display. Raw _va / _vb / _il still drive the inner PI and
            # safety guards just above/below this block.
            # Rebuilding this ~25-field dict at the full 1 kHz tick churns the
            # heap and triggers GC pauses that stall the core-1 WiFi/HTTP
            # thread during the 20 Hz cycle-test logging. 50 Hz is 2.5x the
            # dashboard poll rate, so the displayed data is unaffected. Energy
            # integration and the inner PI below still run every tick.
            _tlm_cnt += 1
            if _tlm_cnt >= 20:
                _tlm_cnt = 0
                state['tlm'] = {
                    'role':        'cap',
                    'v_cap':       _va_lp,
                    'vb_bus':      _vb_lp,
                    'iL':          _il_lp,
                    'p_cap':       _p_lp,                # bus-side V*I (see header)
                    'p_avg3s':     _p_avg3s,
                    'soc_pct':     soc_pct(_va_lp),
                    'energy_J':    energy_J(_va_lp),
                    'i_cmd':       i_cmd_raw,
                    'i_cmd_eff':   i_cmd_eff,
                    'pwm':         int(_pwm_out),
                    'trip':        _trip_active,
                    'trip_reason': _trip_reason,
                    'enable':      1 if enabled else 0,
                    'wd':          0,
                    # ---- Cycle test (efficiency characterisation) ----
                    'test_phase':           _test_phase,
                    'test_t_ms':            (time.ticks_diff(time.ticks_ms(), _test_t_start)
                                             if _test_phase != 'idle' else 0),
                    'test_i_charge_set':    _test_i_charge,
                    'test_i_discharge_set': _test_i_discharge,
                    'test_E_in_J':          _test_E_in,
                    'test_E_out_J':         _test_E_out,
                    'test_E_cap_start_J':   _test_E_cap_start,
                    'test_E_cap_peak_J':    _test_E_cap_peak,
                    'test_E_cap_end_J':     _test_E_cap_end,
                    'test_eta_charge':      _test_eta_charge,
                    'test_eta_discharge':   _test_eta_discharge,
                    'test_eta_roundtrip':   _test_eta_roundtrip,
                }

            # ---- Safety guards ----
            if _va > V_CAP_OVERVOLT:
                _trip_active = 1; _trip_reason = 'cap_overvolt'
                _reset_controllers(); pwm.duty_u16(PWM_MIN)
            elif _vb < VB_CRASH:
                _trip_active = 1; _trip_reason = 'bus_collapse'
                _reset_controllers(); pwm.duty_u16(PWM_MIN)
            elif _vb > VB_OVERVOLT:
                _trip_active = 1; _trip_reason = 'bus_overvolt'
                _reset_controllers(); pwm.duty_u16(PWM_MIN)
            elif abs(_il) > I_TRIP_ABS:
                _trip_active = 1; _trip_reason = 'overcurrent'
                _reset_controllers(); pwm.duty_u16(PWM_MIN)
            elif not enabled:
                _trip_active = 0; _trip_reason = ''
                _reset_controllers(); pwm.duty_u16(PWM_MIN)
            else:
                _trip_active = 0; _trip_reason = ''

                # ---- Inner current loop (1 kHz) — bidirectional with feedforward ----
                # Feedforward is the boost equilibrium duty cycle: D = 1 - Vb/Va.
                # At this duty the inductor sees zero net volt-seconds per cycle,
                # so iL holds constant. Without it the integrator has to generate
                # the entire steady-state PWM, and when i_cmd jumps to 0 the PI
                # can drive PWM all the way to PWM_MIN=0 transiently — which in
                # this synchronous-boost topology clamps HMOS on, dumping cap
                # energy back into the bus and crashing the bus rail.
                # CRITICAL: use VB_NOMINAL, not the measured _vb. Measured Vb in
                # the FF creates a 1.7x positive-feedback loop (bus droops -> FF
                # cranks PWM up -> draws more from bus -> droops more). Using a
                # constant nominal kills the runaway; the PI integrator picks up
                # any actual-vs-nominal Vbus offset as a small steady-state
                # correction.
                d_ff      = max(0.0, 1.0 - VB_NOMINAL / max(_va, 0.5))
                pwm_ff    = d_ff * 65535
                i_err     = i_cmd_eff - _il
                i_int_try = sat(_i_err_int + i_err, I_ERR_INT_LIMIT, -I_ERR_INT_LIMIT)
                pwm_try   = sat(pwm_ff + KP_I * i_err + KI_I * i_int_try, PWM_MAX, PWM_MIN)
                if PWM_MIN < pwm_try < PWM_MAX:
                    _i_err_int = i_int_try
                _pwm_out = pwm_try
                # BOOST: no inversion.
                pwm.duty_u16(int(_pwm_out))

            _print_cnt += 1
            if _print_cnt >= 500:
                _print_cnt = 0
                print('[cap] Vcap={:.2f} Vbus={:.2f} iL={:+.3f} P={:+.2f}W '
                      'P_3s={:+.2f}W i_cmd={:+.3f}/{:+.3f} soc={:.0f}% pwm={}'
                      .format(_va_lp, _vb_lp, _il_lp, _p_lp, _p_avg3s,
                              i_cmd_raw, i_cmd_eff, soc_pct(_va_lp), int(_pwm_out)))
        else:
            # No tick pending: idle this core until the next timer interrupt so
            # the busy-spin does not starve the core-1 WiFi/HTTP thread.
            idle()

except KeyboardInterrupt:
    print("\n[cap] interrupted -- entering safe state...")
finally:
    try:    loop_timer.deinit()
    except Exception: pass
    try:    pwm.duty_u16(PWM_MIN)
    except Exception: pass
    state['shutdown'] = True
    time.sleep_ms(700)
    print("[cap] safe. PWM gated off, timer stopped, HTTP server stopped.")
