# export_smps.py — Export buck SMPS, bus voltage regulator in dissipate direction.
#
# Hardware: Bidirectional Buck/Boost SMPS Module. Set BU/BO switch to BUCK.
#   Port A = bus (10 V nominal), Port B = dummy resistor bank.
#
# Control:
#   Outer loop: voltage PI on the bus, but with the error sign FLIPPED relative
#   to the grid module. Pushes more dissipation when bus is ABOVE target.
#     v_err = v_bus - vb_target
#     i_ref = PI_v(v_err), clamped to [0, I_REF_HI]
#   Inner loop: current PI servoing iL → pwm_out.
#
# Symmetric-droop role: vb_target = 10.1 V (higher than grid's 9.9 V).
# Export sinks only when the bus overshoots, idles in the 9.9–10.1 deadband.
#
# Telemetry:  { role, vb_bus, v_resistor, iL, i_ref, pwm, trip, vb_target }
# Commands:   { enable, vb_target, i_ref_max }
#     i_ref_max acts as a max-dissipation cap, useful if your resistor or
#     scheduler imposes one. Default 1.0 A (~10 W).

import time
from machine import Pin, ADC, I2C, PWM, Timer
from common import (PI, INA219, saturate, wifi_connect, start_http_thread,
                    watchdog_tripped, PWM_FREQ_HZ, PWM_MIN, PWM_MAX,
                    VB_HI_TRIP, VB_LO_TRIP, I_TRIP_ABS, TICK_HZ)

# ---------------- Hardware ----------------

va_pin  = ADC(Pin(28))   # Port A = bus
vb_pin  = ADC(Pin(26))   # Port B = dummy resistor
pwm     = PWM(Pin(9))
pwm.freq(PWM_FREQ_HZ)
ina_i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=2_400_000)

def read_va():
    return (12490 / 2490) * 3.3 * (va_pin.read_u16() / 65536)

def read_vb():
    return (12490 / 2490) * 3.3 * (vb_pin.read_u16() / 65536)

# ---------------- Tuning ----------------

VB_TARGET_DEFAULT = 10.2   # bring-up: wide 1 V deadband with grid at 9.5
                           # narrow to 9.9/10.1 once the loops are tuned and noise is bounded
KP_V, KI_V = 0.5, 5.0
KP_I, KI_I = 100, 300
I_REF_HI   = 2.0          # max dissipation cap. 5 ohm load at ~10 V bus -> 2 A, 20 W.
                          # Sized to worst-case export surplus (PV + supercap peak);
                          # sits under the 2.8 A I_TRIP_ABS. Derives pi_v.out_hi / i_hi below.

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

print("Export SMPS booting...")
ina = INA219(ina_i2c)
wlan = wifi_connect("export")
print("Local IPv4:", wlan.ifconfig()[0] if wlan.isconnected() else "NOT CONNECTED")
start_http_thread(state)

# Tight integrator bounds == clamping anti-windup. Without them, the default
# PI class lets integ run to ±10000, which at KI_V=5 is 50000x past the value
# (I_REF_HI/KI_V) that already saturates the output. That extra wind-up takes
# many seconds to unwind, producing low-frequency limit cycling on the bus
# (visible as bus voltage swinging ~8–12 V at ~1 Hz when PV and export run
# alone without grid). Bounding integ to [0, I_REF_HI/KI_V] means it can wind
# up just enough to saturate, and unwinds in O(error) time.
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

# Soft-start grace: during bring-up the bus may sit at ~0 V before the grid
# module energises it, which would latch an undervolt trip on tick 0. Mask the
# undervolt trip for STARTUP_GRACE_TICKS whenever the controller transitions
# from inactive to active (enable rises, watchdog clears, or trip is reset).
# Over-volt and over-current stay armed throughout. (Export only sinks, so the
# grace just lets us wait for another source to lift the bus — pi_v output
# clamps to 0 while va < target anyway.)
STARTUP_GRACE_TICKS = 500     # 500 ms at TICK_HZ = 1000
startup_grace = 0
prev_active   = False

# ---------------- Main loop ----------------

try:
    while True:
        if timer_elapsed:
            timer_elapsed = 0

            va = read_va()      # bus
            vb = read_vb()      # resistor side
            iL = ina.iL()       # current into resistor (positive = dissipating)

            cmd     = state['cmd']
            target  = cmd.get('vb_target', VB_TARGET_DEFAULT)
            i_max   = min(I_REF_HI, max(0.0, cmd.get('i_ref_max', I_REF_HI)))
            wd      = watchdog_tripped(state, time.ticks_ms())
            # vb_target <= 0.1 V means "off" — scheduler hands the bus to grid.
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
            if va > VB_HI_TRIP or (uv_armed and va < VB_LO_TRIP) or abs(iL) > I_TRIP_ABS:
                if not trip_latched:
                    if va > VB_HI_TRIP:                trip_reason = 'bus_overvolt'
                    elif uv_armed and va < VB_LO_TRIP: trip_reason = 'bus_undervolt'
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
                # SIGN FLIPPED vs grid: act when bus is HIGH, not low.
                v_err   = va - target
                i_ref   = pi_v.step(v_err)
                i_err   = i_ref - iL
                pwm_out = int(pi_i.step(i_err))

            duty = 65536 - pwm_out
            pwm.duty_u16(duty)

            state['tlm'] = {
                'role':       'export',
                'vb_bus':     va,
                'v_resistor': vb,
                'iL':         iL,
                'p_dissip':   vb * iL,
                'i_ref':      i_ref,
                'pwm':        pwm_out,
                'trip':       trip_latched,
                'trip_reason': trip_reason,
                'vb_target':  target,
                'i_ref_max':  i_max,
                'enable':     1 if enabled else 0,
                'wd':         1 if wd else 0,
                'grace':      startup_grace,
            }

            cnt += 1
            if cnt >= 500:
                print("[exp] vbus=%.2f vres=%.2f iL=%+.3f iref=%.3f pwm=%d tgt=%.2f trip=%d wd=%d grace=%d" %
                      (va, vb, iL, i_ref, pwm_out, target, trip_latched, 1 if wd else 0, startup_grace))
                cnt = 0
except KeyboardInterrupt:
    print("\n[exp] interrupted — entering safe state...")
finally:
    try: loop_timer.deinit()
    except Exception: pass
    try: pwm.duty_u16(65535)        # hardware inverts → MOSFET fully off
    except Exception: pass
    state['shutdown'] = True
    time.sleep_ms(700)
    print("[exp] safe. PWM gated off, timer stopped, HTTP server stopped.")
