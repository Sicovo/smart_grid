# pv_smps.py — PV boost SMPS with constant-voltage MPPT.
# Direct port of the known-good reference; control runs in Timer interrupt.
#
# Hardware: Bidirectional Buck/Boost SMPS Module.
#   Switches: BU/BO → BOOST,  OL/CL → CL,  HMOS + LMOS both ON.
#   Port A = bus (10 V nominal), Port B = PV panel (~6 V).
#
# BOOST polarity: pwm.duty_u16(pwm_out) — NOT inverted (the lab's
#   "65536 - pwm_out" trick is buck-specific).
#
# MPPT modes (set via dashboard or MPPT_MODE constant below):
#   'fixed' → vmpp_target = VMPP_TARGET (6.23 V, original behaviour, untouched)
#   'web'   → fetches /sun from icelec50015 every 5 s, maps irradiance → Vmpp
#             via lookup table built from IV characterisation data.
#             sun/tick values are exposed in telemetry for Group 3 logging.
#
# Telemetry: { role, vb_bus, v_panel, iL, p_panel, i_ref, pwm,
#              trip, trip_reason, vmpp_target, enable, wd,
#              mppt_mode, irradiance, web_tick }
# Commands:  { enable, vmpp_target, reset_trip, mppt_mode }

import time
from machine import Pin, ADC, I2C, PWM, Timer
from common import wifi_connect, start_http_thread

# ============================================================
# Hardware
# ============================================================

va_pin = ADC(Pin(28))
vb_pin = ADC(Pin(26))
pwm    = PWM(Pin(9))
pwm.freq(100_000)
i2c    = I2C(0, scl=Pin(1), sda=Pin(0), freq=2_400_000)
ADDR, SHUNT = 0x40, 0.10

def ina_init():
    i2c.writeto_mem(ADDR, 0x00, b'\x1D\xDF')
    i2c.writeto_mem(ADDR, 0x05, b'\x00\x00')

def ina_current():
    # Shunt wired A->B (buck-positive); boost flows B->A, so negate.
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

# ============================================================
# Tuning — ORIGINAL VALUES, UNTOUCHED
# ============================================================

VMPP_TARGET = 6.23
KP_V, KI_V  = 0.4,  0.02
KP_I, KI_I  = 100,  200
PWM_MIN     = 0
PWM_MAX     = 45000         # approx 69% duty cap
I_REF_MAX   = 1.5
I_ERR_INT_LIMIT    = 500.0
V_ERR_INT_LIMIT    = 50.0
VB_CRASH_THRESHOLD = 2.0    # panel collapse -> reset and wait
VA_OVERVOLTAGE     = 13.0   # bus runaway -> reset
I_TRIP_ABS_LOCAL   = 2.8    # hardware overcurrent

# ============================================================
# Web MPPT — lookup table + helpers
# ============================================================

# Default mode: 'fixed' keeps original behaviour.
# Switch to 'web' via dashboard:  pv  mppt_mode  web
MPPT_MODE = 'fixed'

# Vmpp vs irradiance fraction — built from IV characterisation.
# Replace the two placeholder rows once you have measured those sweeps.
# Format: (irradiance_fraction, Vmpp_volts)
VMPP_TABLE = [
    (0.10, 5.65),   # Vmpp at 10% irradiance
    (0.25, 5.88),   # Vmpp at 20% irradiance
    (0.35, 6.05),   # Vmpp at 35% irradiance
    (0.50, 6.08),   # Vmpp at 50% irradiance — you have this, just refine the knee
    (0.65, 6.13),   # Vmpp at 65% irradiance
    (0.80, 6.22),   # Vmpp at 80% irradiance
    (1.00, 6.43),   # Vmpp at 100% irradiance — you have this, just refine the knee
]

def vmpp_from_irradiance(irr):
    """Return interpolated Vmpp (V) for irradiance fraction 0.0-1.0.
    Clamps to table extremes rather than extrapolating."""
    irr = max(0.0, min(1.0, irr))
    if irr <= VMPP_TABLE[0][0]:
        return VMPP_TABLE[0][1]
    if irr >= VMPP_TABLE[-1][0]:
        return VMPP_TABLE[-1][1]
    for i in range(len(VMPP_TABLE) - 1):
        x0, y0 = VMPP_TABLE[i]
        x1, y1 = VMPP_TABLE[i + 1]
        if x0 <= irr <= x1:
            t = (irr - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return VMPP_TABLE[-1][1]

def fetch_sun():
    """GET icelec50015.azurewebsites.net/sun -> (irradiance_fraction, tick).
    'sun' arrives as 0-100; divide by 100 to get 0.0-1.0.
    Returns (None, None) on any network or parse error.
    NOTE: never call this inside the timer callback — network I/O blocks."""
    try:
        import urequests
        r = urequests.get(
            'http://icelec50015.azurewebsites.net/sun',
            timeout=2
        )
        j = r.json()
        r.close()
        return j['sun'] / 100.0, j['tick']
    except Exception as e:
        print('[pv] fetch_sun failed:', e)
        return None, None

# Sun-fetch state — written by main loop, read inside timer flag block.
# Simple float/int assignments are atomic enough in MicroPython.
_web_irradiance     = 1.0   # last good irradiance fraction (default full sun)
_web_tick           = None  # last good server tick
_last_sun_fetch_ms  = 0
_SUN_FETCH_INTERVAL = 5000  # ms — matches server tick rate

# ============================================================
# Shared state (dashboard-compatible)
# ============================================================

state = {
    'cmd':         {'enable': 1, 'vmpp_target': VMPP_TARGET},
    'tlm':         {},
    'last_cmd_ms': time.ticks_ms(),
}

# ============================================================
# Control state
# ============================================================

_v_err_int   = 0.0
_i_err_int   = 0.0
_i_ref       = 0.0
_pwm_out     = PWM_MIN
_outer_cnt   = 0
_print_cnt   = 0
_trip_active = 0
_trip_reason = ''

def _reset_controllers():
    global _v_err_int, _i_err_int, _i_ref, _pwm_out
    _v_err_int = 0.0
    _i_err_int = 0.0
    _i_ref     = 0.0
    _pwm_out   = PWM_MIN

# ============================================================
# Timer flag — teammate's fix:
# Timer only sets a flag; all control and network calls run in the
# main loop so Ctrl+C is caught instantly and fetch_sun() never
# blocks the interrupt.
# ============================================================

timer_elapsed = 0
def tick(_t):
    global timer_elapsed
    timer_elapsed = 1

# ============================================================
# Boot
# ============================================================

print("PV SMPS booting...")
ina_init()
pwm.duty_u16(PWM_MIN)
wlan = wifi_connect("pv")
print("WiFi:", wlan.ifconfig() if wlan.isconnected() else "NOT CONNECTED")
start_http_thread(state)

loop_timer = Timer(mode=Timer.PERIODIC, freq=1000, callback=tick)
print("[pv] running. Ctrl+C to stop.")
print("[pv] MPPT mode:", MPPT_MODE,
      "-- send  pv mppt_mode web  from dashboard to enable web MPPT.")

# ============================================================
# Main loop
#
# Two things happen here:
#   A) Every 1 ms (timer_elapsed):  read sensors, run PI loops, update PWM
#   B) Every 5 s  (web mode only):  fetch /sun, update _web_irradiance
#
# B runs OUTSIDE the timer_elapsed gate so the 1 ms control tick is
# never stalled waiting for a network response. If fetch_sun() takes
# up to 2 s, the timer interrupt keeps firing and sets timer_elapsed
# throughout — we simply catch up on the next iteration.
# ============================================================

try:
    while True:

        # ---- B: Sun fetch (web mode only, every 5 s) ----
        # Not gated by timer_elapsed — runs freely in the main loop.
        current_mode = state['cmd'].get('mppt_mode', MPPT_MODE)
        if current_mode == 'web':
            now_ms = time.ticks_ms()
            if time.ticks_diff(now_ms, _last_sun_fetch_ms) >= _SUN_FETCH_INTERVAL:
                irr, tick_val = fetch_sun()
                _last_sun_fetch_ms = now_ms
                if irr is not None:
                    _web_irradiance = irr
                    _web_tick       = tick_val
                    print('[pv] sun fetch -> irr={:.2f}  tick={}  vmpp={:.3f}V'
                          .format(irr, tick_val, vmpp_from_irradiance(irr)))
                # If fetch failed, _web_irradiance holds its last good value.

        # ---- A: 1 kHz control tick ----
        if not timer_elapsed:
            continue
        timer_elapsed = 0

        _vb = read_vb()
        _il = ina_current()
        _va = read_va()

        cmd     = state['cmd']
        enabled = bool(cmd.get('enable', 1))

        # Decide vmpp_target based on active mode.
        # 'web'   -> irradiance from server -> lookup table
        # 'fixed' -> cmd override or hardcoded 6.23 V (original behaviour)
        mode = cmd.get('mppt_mode', MPPT_MODE)
        if mode == 'web':
            vmp_target = vmpp_from_irradiance(_web_irradiance)
        else:
            vmp_target = cmd.get('vmpp_target', VMPP_TARGET)

        # Dashboard reset button (no latch, but kick PIs)
        if cmd.get('reset_trip', 0):
            cmd['reset_trip'] = 0
            _reset_controllers()

        # ---- Telemetry (every tick) ----
        state['tlm'] = {
            'role':        'pv',
            'vb_bus':      _va,
            'v_panel':     _vb,
            'iL':          _il,
            'p_panel':     _vb * _il,
            'i_ref':       _i_ref,
            'vmpp_target': vmp_target,
            'pwm':         int(_pwm_out),
            'trip':        _trip_active,
            'trip_reason': _trip_reason,
            'enable':      1 if enabled else 0,
            'wd':          0,
            # web MPPT extras
            'mppt_mode':   mode,
            'irradiance':  _web_irradiance,
            'web_tick':    _web_tick,
        }

        # ---- Safety guards (non-latching; auto-recover) ----
        if _vb < VB_CRASH_THRESHOLD:
            _trip_active = 1
            _trip_reason = 'panel_collapse'
            _reset_controllers()
            pwm.duty_u16(PWM_MIN)
        elif _va > VA_OVERVOLTAGE:
            _trip_active = 1
            _trip_reason = 'bus_overvolt'
            _reset_controllers()
            pwm.duty_u16(PWM_MIN)
        elif abs(_il) > I_TRIP_ABS_LOCAL:
            _trip_active = 1
            _trip_reason = 'overcurrent'
            _reset_controllers()
            pwm.duty_u16(PWM_MIN)
        elif not enabled:
            _trip_active = 0
            _trip_reason = ''
            _reset_controllers()
            pwm.duty_u16(PWM_MIN)
        else:
            _trip_active = 0
            _trip_reason = ''

            # ---- Outer loop (100 Hz) ----
            _outer_cnt += 1
            if _outer_cnt >= 10:
                _outer_cnt = 0
                v_err     = _vb - vmp_target
                v_int_try = sat(_v_err_int + v_err, V_ERR_INT_LIMIT, -V_ERR_INT_LIMIT)
                i_ref_try = sat(KP_V * v_err + KI_V * v_int_try, I_REF_MAX, 0.0)
                if 0.0 < i_ref_try < I_REF_MAX:
                    _v_err_int = v_int_try
                _i_ref = i_ref_try

            # ---- Voltage override (panel below target, outer saturated low) ----
            if _i_ref == 0.0 and (_vb - vmp_target) < -0.05:
                _pwm_out   = max(PWM_MIN, _pwm_out - 20)
                _i_err_int = 0.0
                pwm.duty_u16(int(_pwm_out))
            else:
                # ---- Inner loop (1 kHz) ----
                i_err     = _i_ref - _il
                i_int_try = sat(_i_err_int + i_err, I_ERR_INT_LIMIT, -I_ERR_INT_LIMIT)
                pwm_try   = sat(KP_I * i_err + KI_I * i_int_try, PWM_MAX, PWM_MIN)
                if PWM_MIN < pwm_try < PWM_MAX:
                    _i_err_int = i_int_try
                _pwm_out = pwm_try
                # BOOST: no inversion
                pwm.duty_u16(int(_pwm_out))

        _print_cnt += 1
        if _print_cnt >= 500:
            _print_cnt = 0
            print('[pv] Va={:.2f} Vb={:.3f} iL={:+.3f} P={:+.2f}W '
                  'iref={:.3f} pwm={} mode={} irr={:.2f} vmpp_tgt={:.3f}'
                  .format(_va, _vb, _il, _vb * _il,
                          _i_ref, int(_pwm_out), mode,
                          _web_irradiance, vmp_target))

except KeyboardInterrupt:
    print("\n[pv] interrupted -- entering safe state...")
finally:
    try:    loop_timer.deinit()
    except Exception: pass
    try:    pwm.duty_u16(PWM_MIN)
    except Exception: pass
    state['shutdown'] = True
    time.sleep_ms(700)
    print("[pv] safe. PWM gated off, timer stopped, HTTP server stopped.")
