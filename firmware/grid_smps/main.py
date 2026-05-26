# grid_smps.py — Grid buck SMPS, bus voltage regulator in import direction.
#
# Hardware: Bidirectional Buck/Boost SMPS Module. Set BU/BO switch to BUCK.
#   Port A = 12 V bench PSU, Port B = bus (10 V nominal).
#
# Control:
#   Outer loop: voltage PI on the bus. Pushes more current when bus is BELOW target.
#     v_err = vb_target - v_bus
#     i_ref = PI_v(v_err), clamped to [0, I_REF_HI]   (cannot push back into PSU)
#   Inner loop: current PI servoing iL → pwm_out.
#
# Symmetric-droop role: vb_target = 9.9 V (lower than export's 10.1 V).
# Grid sources when the bus sags below 9.9, idles in the 9.9–10.1 deadband,
# stays idle when the bus is high (export will handle that side).
#
# Telemetry:  { role, v_psu, vb_bus, iL, i_ref, pwm, trip, vb_target }
# Commands:   { enable, vb_target, i_ref_max }
#     vb_target = 0 (or enable = 0) forces the module fully idle, which is how
#     a higher-level scheduler can hand the bus off entirely to export.

import socket, json, _thread, time
from machine import Pin, ADC, I2C, PWM, Timer
from common import (PI, INA219, saturate, wifi_connect, start_http_thread,
                    watchdog_tripped, PWM_FREQ_HZ, PWM_MIN, PWM_MAX,
                    VB_HI_TRIP, VB_LO_TRIP, I_TRIP_ABS, TICK_HZ)

# ---------------- Hardware ----------------

va_pin  = ADC(Pin(28))   # Port A = 12 V PSU
vb_pin  = ADC(Pin(26))   # Port B = bus
pwm     = PWM(Pin(9))
pwm.freq(PWM_FREQ_HZ)
ina_i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=2_400_000)

def read_va():
    return (12490 / 2490) * 3.3 * (va_pin.read_u16() / 65536)

def read_vb():
    return (12490 / 2490) * 3.3 * (vb_pin.read_u16() / 65536)

# ---------------- Tuning ----------------

VB_TARGET_DEFAULT = 9.8    # bring-up: wide 1 V deadband with export at 10.5
                           # narrow to 9.9/10.1 once the loops are tuned and noise is bounded
KP_V, KI_V = 0.5, 5.0     # outer bus-voltage loop
KP_I, KI_I = 100, 300     # inner current loop — same shape as bidirectional template
I_REF_HI   = 2.0          # max import current (~20 W from 10 V bus)

# ---------------- State ----------------

state = {
    'cmd':  {'enable': 1, 'vb_target': VB_TARGET_DEFAULT, 'i_ref_max': I_REF_HI},
    'tlm':  {},
    'last_cmd_ms': time.ticks_ms(),
}

timer_elapsed = 0
def tick(_t):
    global timer_elapsed
    timer_elapsed = 1

# ---------------- Boot ----------------

print("Grid SMPS booting...")
ina = INA219(ina_i2c)
wlan = wifi_connect("grid")
print("WiFi:", wlan.ifconfig() if wlan.isconnected() else "NOT CONNECTED")
start_http_thread(state)

# Tight integrator bounds == clamping anti-windup. Without them, the default
# PI class lets integ run to ±10000, which at KI_V=5 is 50000x past the value
# (I_REF_HI/KI_V) that already saturates the output. That extra wind-up takes
# many seconds to unwind, producing low-frequency limit cycling on the bus.
# Bounding integ to [0, I_REF_HI/KI_V] means it can wind up just enough to
# saturate, and unwinds in O(error) time once the bus comes back to target.
pi_v = PI(KP_V, KI_V, out_lo=0.0, out_hi=I_REF_HI,
          i_lo=0.0, i_hi=I_REF_HI / KI_V)
pi_i = PI(KP_I, KI_I, out_lo=float(PWM_MIN), out_hi=float(PWM_MAX),
          i_lo=float(PWM_MIN) / KI_I, i_hi=float(PWM_MAX) / KI_I)

trip_latched = 0
trip_reason  = ''
i_ref   = 0.0
pwm_out = PWM_MIN
loop_timer = Timer(mode=Timer.PERIODIC, freq=TICK_HZ, callback=tick)
cnt = 0

# Soft-start grace: when grid is the only source on the bus (bring-up or after
# the bus has discharged), vb starts at ~0 V and the undervolt trip would latch
# on tick 0 — before PWM has had a chance to push the bus up. Mask the
# undervolt trip for STARTUP_GRACE_TICKS whenever the controller transitions
# from inactive to active (enable rises, watchdog clears, or trip is reset).
# Over-volt and over-current stay armed throughout.
STARTUP_GRACE_TICKS = 500     # 500 ms at TICK_HZ = 1000
startup_grace = 0
prev_active   = False

# ---------------- Main loop ----------------

try:
    while True:
        if timer_elapsed:
            timer_elapsed = 0

            va = read_va()      # 12 V PSU
            vb = read_vb()      # bus
            iL = ina.iL()       # current into bus (positive = import)

            cmd     = state['cmd']
            target  = cmd.get('vb_target', VB_TARGET_DEFAULT)
            i_max   = min(I_REF_HI, max(0.0, cmd.get('i_ref_max', I_REF_HI)))
            wd      = watchdog_tripped(state, time.ticks_ms())
            # vb_target <= 0.1 V means "off" — scheduler hands the bus to export.
            enabled = bool(cmd.get('enable', 0)) and target > 0.1

            # Trip reset from dashboard (one-shot). Re-latches next tick if the
            # fault persists, unless the grace window masks it.
            if cmd.get('reset_trip', 0):
                cmd['reset_trip'] = 0
                trip_latched = 0
                trip_reason  = ''

            # Rising edge of "controller will run this tick" → arm grace window.
            # Catches enable 0→1, wd clear, and trip reset all in one check.
            active = enabled and not trip_latched and not wd
            if active and not prev_active:
                startup_grace = STARTUP_GRACE_TICKS
            prev_active = active

            uv_armed = active and startup_grace <= 0
            if vb > VB_HI_TRIP or (uv_armed and vb < VB_LO_TRIP) or abs(iL) > I_TRIP_ABS:
                if not trip_latched:
                    if vb > VB_HI_TRIP:                trip_reason = 'bus_overvolt'
                    elif uv_armed and vb < VB_LO_TRIP: trip_reason = 'bus_undervolt'
                    else:                              trip_reason = 'overcurrent'
                trip_latched = 1

            if startup_grace > 0:
                startup_grace -= 1

            if (not enabled) or trip_latched or wd:
                i_ref   = 0.0
                pi_v.reset()
                pi_i.reset()
                pwm_out = PWM_MIN
            else:
                pi_v.hi   = i_max
                pi_v.i_hi = i_max / KI_V    # keep anti-windup limit in sync
                v_err   = target - vb
                i_ref   = pi_v.step(v_err)
                i_err   = i_ref - iL
                pwm_out = int(pi_i.step(i_err))

            duty = 65536 - pwm_out
            pwm.duty_u16(duty)

            state['tlm'] = {
                'role':      'grid',
                'v_psu':     va,
                'vb_bus':    vb,
                'iL':        iL,
                'p_import':  vb * iL,
                'i_ref':     i_ref,
                'pwm':       pwm_out,
                'trip':      trip_latched,
                'trip_reason': trip_reason,
                'vb_target': target,
                'i_ref_max': i_max,
                'enable':    1 if enabled else 0,
                'wd':        1 if wd else 0,
                'grace':     startup_grace,
            }

            cnt += 1
            if cnt >= 500:
                print("[grid] vbus=%.2f iL=%+.3f iref=%.3f pwm=%d tgt=%.2f trip=%d wd=%d grace=%d" %
                      (vb, iL, i_ref, pwm_out, target, trip_latched, 1 if wd else 0, startup_grace))
                cnt = 0
except KeyboardInterrupt:
    print("\n[grid] interrupted — entering safe state...")
finally:
    try: loop_timer.deinit()
    except Exception: pass
    try: pwm.duty_u16(65535)        # hardware inverts → MOSFET fully off
    except Exception: pass
    state['shutdown'] = True
    time.sleep_ms(700)
    print("[grid] safe. PWM gated off, timer stopped, HTTP server stopped.")
