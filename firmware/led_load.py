# led_load.py — Triple LED CC driver. Three independent current PIs on one Pico W.
#
# Hardware: Triple LED Driver assembly. Different from the bidirectional SMPS
#   modules — uses an SPI ADC (MCP3208-style) for sensing instead of an INA219,
#   and the shunt is 330 mΩ so iL = 3 × Vshunt.
#
#   PWM out:     red=GP11   yel=GP9   grn=GP7
#   Enable pins: red=GP10   yel=GP8   grn=GP6   (must be HIGH for the gate driver to pass PWM)
#   SPI ADC:     channels 0,2,4 = i_grn,i_yel,i_red   channels 1,3,5 = v_grn,v_yel,v_red
#   ADC CS:      GP17
#
# Control: per-channel current PI. Setpoint comes from p_demand:
#     v_LED = 2 * v_v_pin - v_i_pin              (LED forward voltage)
#     i_ref = p_demand / v_LED                   (clamped to I_MAX_PER_CH)
#     i_err = i_ref - i_ch
#     pwm   = PI(i_err)
#
# Enable gating: when p_demand = 0 the enable pin goes LOW and the PI is reset.
# Avoids the integrator winding up while the channel is meant to be off.
#
# Telemetry:  { role, trip, i_{red,yel,grn}, v_{red,yel,grn}, ir_{red,yel,grn}, d_{red,yel,grn} }
# Commands:   { enable, p_red, p_yel, p_grn }

import socket, json, _thread, time
from machine import Pin, SPI, PWM, Timer
from common import (PI, saturate, wifi_connect, start_http_thread,
                    watchdog_tripped, PWM_FREQ_HZ, TICK_HZ)

# ---------------- Hardware (Triple_LED_Driver_Example.py pin map) ----------------

pwm_red = PWM(Pin(11));  pwm_red.freq(PWM_FREQ_HZ)
pwm_yel = PWM(Pin(9));   pwm_yel.freq(PWM_FREQ_HZ)
pwm_grn = PWM(Pin(7));   pwm_grn.freq(PWM_FREQ_HZ)

en_red = Pin(10, Pin.OUT); en_red.value(0)
en_yel = Pin(8,  Pin.OUT); en_yel.value(0)
en_grn = Pin(6,  Pin.OUT); en_grn.value(0)

spi    = SPI(0, baudrate=400_000)
adc_cs = Pin(17, mode=Pin.OUT, value=1)

def readadc(channel):
    """Single-shot MCP3208-style read. Returns 12-bit raw count [0, 4095]."""
    tx = bytearray([6 + (channel >> 2), (channel & 3) << 6, 0])
    rx = bytearray(len(tx))
    try:
        adc_cs(0)
        time.sleep_us(10)
        spi.write_readinto(tx, rx)
    finally:
        adc_cs(1)
    return ((rx[1] & 15) << 8) + rx[2]

ADC_VREF = 2.497  # from Triple_LED_Driver_Example.py

# Per-channel config: (name, adc_i_ch, adc_v_ch, pwm_obj, en_pin)
CHANNELS = [
    ('red', 4, 5, pwm_red, en_red),
    ('yel', 2, 3, pwm_yel, en_yel),
    ('grn', 0, 1, pwm_grn, en_grn),
]

# ---------------- Tuning ----------------

# Gains differ from the bidirectional template because the LED driver has a
# 330 mΩ shunt (vs 100 mΩ) and the loop output is directly PWM_u16 units.
# These are starting points — tune at the bench against a known-good step.
KP_I, KI_I       = 800.0, 200.0
PWM_LO, PWM_HI   = 100, 62500     # matches the example's saturate() bounds
P_MAX_PER_CH     = 3.0            # W — datasheet rating
I_MAX_PER_CH     = 1.05           # A — datasheet rating
V_LED_FLOOR      = 0.5            # V — guards 1/v_LED when LED is dark

# ---------------- State ----------------

state = {
    'cmd':  {'enable': 1, 'p_red': 0.0, 'p_yel': 0.0, 'p_grn': 0.0},
    'tlm':  {},
    'last_cmd_ms': time.ticks_ms(),
}

timer_elapsed = 0
def tick(_t):
    global timer_elapsed
    timer_elapsed = 1

# ---------------- Boot ----------------

print("LED load booting...")
wlan = wifi_connect("led")
print("WiFi:", wlan.ifconfig() if wlan.isconnected() else "NOT CONNECTED")
start_http_thread(state)

# One PI per channel
pis = {name: PI(KP_I, KI_I, out_lo=float(PWM_LO), out_hi=float(PWM_HI))
       for name, _, _, _, _ in CHANNELS}

trip_latched = 0
trip_reason  = ''

# ---------------- Boot-time ADC diagnostic ----------------
# Sample each SPI ADC channel a few times BEFORE the control loop starts, so
# we can see what the sensors read with no PWM commanded. If you see large
# i_ch values here while no LED is conducting, the trip is phantom (floating
# ADC, wrong port, brownout). Remove this block once diagnosed.

print("[led-diag] sampling SPI ADC before main loop...")
for _pass in range(5):
    for _name, _ci, _cv, _, _ in CHANNELS:
        _raw_i = readadc(_ci)
        _raw_v = readadc(_cv)
        _v_i   = ADC_VREF * (_raw_i / 4096.0)
        _v_v   = ADC_VREF * (_raw_v / 4096.0)
        _i_ch  = 3.0 * _v_i
        _v_ch  = 2.0 * _v_v - _v_i
        print("[led-diag] %s  raw_i=%4d raw_v=%4d  v_i=%.3fV v_v=%.3fV  i_ch=%.3fA v_led=%.3fV" %
              (_name, _raw_i, _raw_v, _v_i, _v_v, _i_ch, _v_ch))
    print("---")
    time.sleep_ms(100)
print("[led-diag] trip limit is %.2f A. starting main loop." % (I_MAX_PER_CH * 1.4))

loop_timer = Timer(mode=Timer.PERIODIC, freq=TICK_HZ, callback=tick)
cnt = 0

# ---------------- Main loop ----------------

try:
    while True:
        if timer_elapsed:
            timer_elapsed = 0

            cmd      = state['cmd']

            # Trip reset from dashboard (one-shot). Per-channel checks below
            # immediately re-latch this tick if any channel is still over-current.
            if cmd.get('reset_trip', 0):
                cmd['reset_trip'] = 0
                trip_latched = 0
                trip_reason = ''

            wd       = watchdog_tripped(state, time.ticks_ms())
            enabled  = bool(cmd.get('enable', 0))
            gate_off = (not enabled) or trip_latched or wd

            tlm = {'role': 'led', 'trip': trip_latched, 'trip_reason': trip_reason,
                   'wd': 1 if wd else 0, 'enable': 1 if enabled else 0}

            for name, ch_i, ch_v, pwm_obj, en_pin in CHANNELS:
                v_i_pin = ADC_VREF * (readadc(ch_i) / 4096.0)
                v_v_pin = ADC_VREF * (readadc(ch_v) / 4096.0)
                i_ch    = 3.0 * v_i_pin                                  # 330 mΩ shunt
                v_ch    = max(2.0 * v_v_pin - v_i_pin, V_LED_FLOOR)      # LED forward V

                # Per-channel safety — record WHICH channel tripped
                if i_ch > I_MAX_PER_CH * 1.4:
                    if not trip_latched:
                        trip_reason = 'overcurrent_' + name
                        tlm['trip_reason'] = trip_reason
                    trip_latched = 1
                    tlm['trip'] = 1
                    gate_off = True

                p_dem = saturate(cmd.get('p_' + name, 0.0), P_MAX_PER_CH, 0.0)
                i_ref = saturate(p_dem / v_ch, I_MAX_PER_CH, 0.0)

                if gate_off or p_dem <= 0.001:
                    en_pin.value(0)
                    pis[name].reset()
                    duty_out = PWM_LO
                    pwm_obj.duty_u16(duty_out)
                else:
                    en_pin.value(1)
                    i_err    = i_ref - i_ch
                    duty_out = int(pis[name].step(i_err))
                    pwm_obj.duty_u16(duty_out)

                tlm['i_'  + name] = i_ch
                tlm['v_'  + name] = v_ch
                tlm['p_'  + name] = v_ch * i_ch                # actual power
                tlm['pd_' + name] = p_dem                      # demanded power (setpoint)
                tlm['ir_' + name] = i_ref
                tlm['d_'  + name] = duty_out

            state['tlm'] = tlm

            cnt += 1
            if cnt >= 500:
                print("[led] R:%.2f/%.2f Y:%.2f/%.2f G:%.2f/%.2f trip=%d wd=%d" %
                      (tlm['i_red'], tlm['ir_red'],
                       tlm['i_yel'], tlm['ir_yel'],
                       tlm['i_grn'], tlm['ir_grn'],
                       trip_latched, 1 if wd else 0))
                cnt = 0
except KeyboardInterrupt:
    print("\n[led] interrupted — entering safe state...")
finally:
    try: loop_timer.deinit()
    except Exception: pass
    # Drop enables FIRST — gates PWM off at the driver regardless of duty.
    for _name, _i, _v, pwm_obj, en_pin in CHANNELS:
        try: en_pin.value(0)
        except Exception: pass
        try: pwm_obj.duty_u16(0)
        except Exception: pass
    state['shutdown'] = True
    time.sleep_ms(700)
    print("[led] safe. All channels gated off, timer stopped, HTTP server stopped.")
