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
#   Datasheet 5-second peak current: 350 mA. We clamp |i_cmd| at 0.30 A.
#   Usable window 10.5 V (below this Va<Vb, SMPS can't transfer) to 17.5 V
#   (SMPS port limit, under cap rating). ~49 J of usable energy in that window.
#
# Control architecture: no outer bus-voltage loop — grid/export handle bus
# regulation. The cap is a *commanded* current source/sink. The "outer" is
# just three safety clamps on i_cmd:
#   1. |i_cmd| clamped to I_CAP_MAX (0.30 A).
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
# Telemetry: { role, v_cap, vb_bus, iL, p_cap, soc_pct, energy_J,
#              i_cmd, i_cmd_eff, pwm, trip, trip_reason, enable, wd }
# Commands:  { enable, i_cmd, reset_trip }

import time
from machine import Pin, ADC, I2C, PWM, Timer
from common import wifi_connect, start_http_thread

# ---------------- Hardware ----------------

va_pin = ADC(Pin(28))      # Port A = supercap
vb_pin = ADC(Pin(26))      # Port B = bus
pwm    = PWM(Pin(9))
pwm.freq(100_000)
i2c    = I2C(0, scl=Pin(1), sda=Pin(0), freq=2_400_000)
ADDR, SHUNT = 0x40, 0.10

def ina_init():
    i2c.writeto_mem(ADDR, 0x00, b'\x1D\xDF')
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
    return 1.017 * (12490/2490) * 3.3 * va_pin.read_u16() / 65536

def read_vb():
    return 1.015 * (12490/2490) * 3.3 * vb_pin.read_u16() / 65536

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

# Current command limit — 30% headroom under the 350 mA 5-second rating.
I_CAP_MAX       = 0.30

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
I_TRIP_ABS      = 0.45    # ~50% over the 0.30 A cap; catches a runaway PI fast

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
_trip_active = 0
_trip_reason = ''

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

            _va = read_va()       # cap
            _vb = read_vb()       # bus
            _il = ina_current()   # +ve = charging

            cmd       = state['cmd']
            enabled   = bool(cmd.get('enable', 1))
            i_cmd_raw = float(cmd.get('i_cmd', 0.0))

            # Dashboard reset button — clear trip + integrator.
            if cmd.get('reset_trip', 0):
                cmd['reset_trip'] = 0
                _trip_active = 0
                _trip_reason = ''
                _reset_controllers()

            # Apply soft taper + ±I_CAP_MAX clamp. Disabled => command effectively 0.
            i_cmd_eff = apply_soft_taper(i_cmd_raw, _va) if enabled else 0.0

            # Hard charge cutoff at V_CAP_CHARGE_CUTOFF — force charging to 0
            # once we hit the cap voltage limit. Discharge still allowed.
            if i_cmd_eff > 0.0 and _va >= V_CAP_CHARGE_CUTOFF:
                i_cmd_eff = 0.0

            # Bus-droop awareness: scale charging command down if bus is sagging.
            # Cap_smps shares port B with grid_smps + loadbank. If we keep
            # demanding full charge current while the bus droops, we hit a
            # positive-feedback collapse (bus down -> more PWM -> more demand ->
            # bus further down). Scaling charge demand by bus health breaks that
            # loop. Only applied to charging; discharging into a healthy bus is
            # fine, and discharging into a sagging bus is actually helpful.
            if i_cmd_eff > 0.0:
                vb_scale = (_vb - VB_BACKOFF) / (VB_HEALTHY - VB_BACKOFF)
                if vb_scale < 0.0: vb_scale = 0.0
                elif vb_scale > 1.0: vb_scale = 1.0
                i_cmd_eff = i_cmd_eff * vb_scale

            # ---- Telemetry ----
            state['tlm'] = {
                'role':        'cap',
                'v_cap':       _va,
                'vb_bus':      _vb,
                'iL':          _il,
                'p_cap':       _va * _il,            # +ve = charging power
                'soc_pct':     soc_pct(_va),
                'energy_J':    energy_J(_va),
                'i_cmd':       i_cmd_raw,
                'i_cmd_eff':   i_cmd_eff,
                'pwm':         int(_pwm_out),
                'trip':        _trip_active,
                'trip_reason': _trip_reason,
                'enable':      1 if enabled else 0,
                'wd':          0,
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
                      'i_cmd={:+.3f}/{:+.3f} soc={:.0f}% pwm={}'
                      .format(_va, _vb, _il, _va * _il,
                              i_cmd_raw, i_cmd_eff, soc_pct(_va), int(_pwm_out)))

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
