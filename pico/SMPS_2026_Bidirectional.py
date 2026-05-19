import network
import urequests
import json
import time
import socket
from machine import Pin, I2C, ADC, PWM, Timer

# ── WiFi / backend settings ──────────────────────────────────────────────────
WIFI_SSID = ""
WIFI_PASSWORD = ""
BACKEND_HOST = ""
BACKEND_URL = ""

CONFIG_FILE = "smps_net_config.json"
AP_SSID = "SMPS-Setup"
AP_PASSWORD = "smpssetup123"
AP_IP = "192.168.4.1"
# ─────────────────────────────────────────────────────────────────────────────

wlan = None


def urldecode(value):
    value = value.replace("+", " ")
    parts = value.split("%")
    if len(parts) == 1:
        return value
    out = parts[0]
    for part in parts[1:]:
        if len(part) >= 2:
            try:
                out += chr(int(part[:2], 16)) + part[2:]
            except ValueError:
                out += "%" + part
        else:
            out += "%" + part
    return out


def parse_form_encoded(body):
    parsed = {}
    if not body:
        return parsed
    for pair in body.split("&"):
        if "=" in pair:
            key, value = pair.split("=", 1)
            parsed[urldecode(key)] = urldecode(value)
    return parsed


def normalize_backend_host(host):
    host = host.strip()
    if host.startswith("http://"):
        host = host[7:]
    elif host.startswith("https://"):
        host = host[8:]
    host = host.strip("/")
    if "/" in host:
        host = host.split("/", 1)[0]
    return host


def build_backend_url(host):
    host = normalize_backend_host(host)
    if not host:
        return ""
    if ":" in host:
        return "http://{}/smps/ingest".format(host)
    return "http://{}:8000/smps/ingest".format(host)


def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            cfg = json.loads(f.read())
            return {
                "wifi_ssid": cfg.get("wifi_ssid", ""),
                "wifi_password": cfg.get("wifi_password", ""),
                "backend_host": normalize_backend_host(cfg.get("backend_host", "")),
            }
    except Exception:
        return {"wifi_ssid": "", "wifi_password": "", "backend_host": ""}


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        f.write(json.dumps(cfg))


def apply_network_config(cfg):
    global WIFI_SSID, WIFI_PASSWORD, BACKEND_HOST, BACKEND_URL
    WIFI_SSID = cfg.get("wifi_ssid", "").strip()
    WIFI_PASSWORD = cfg.get("wifi_password", "")
    BACKEND_HOST = normalize_backend_host(cfg.get("backend_host", ""))
    BACKEND_URL = build_backend_url(BACKEND_HOST)


def start_access_point():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.ifconfig((AP_IP, "255.255.255.0", AP_IP, AP_IP))
    if AP_PASSWORD:
        # Some MicroPython builds don't expose AUTH_WPA_WPA2_PSK.
        ap.config(essid=AP_SSID, password=AP_PASSWORD)
    else:
        ap.config(essid=AP_SSID)
    print("AP active: {} on {}".format(AP_SSID, AP_IP))
    return ap


def stop_access_point(ap):
    try:
        ap.active(False)
    except Exception:
        pass


def setup_page_html(cfg, status):
    ssid = cfg.get("wifi_ssid", "")
    wifi_password = cfg.get("wifi_password", "")
    backend = cfg.get("backend_host", "")
    return """HTTP/1.1 200 OK\r
Content-Type: text/html\r
Connection: close\r
\r
<!DOCTYPE html>
<html>
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
  <title>SMPS Setup</title>
  <style>
        body {{ font-family: Arial, sans-serif; max-width: 520px; margin: 24px auto; padding: 0 12px; }}
        input {{ width: 100%; padding: 10px; margin: 6px 0 12px 0; box-sizing: border-box; }}
        button {{ padding: 10px 14px; }}
        .ok {{ color: #0a5; }}
        .warn {{ color: #a50; }}
  </style>
</head>
<body>
  <h2>SMPS Network Setup</h2>
  <p>Connect Pico to your Wi-Fi and backend.</p>
    <p class="warn">{status}</p>
  <form method=\"POST\" action=\"/\">
    <label>Wi-Fi SSID</label>
    <input name=\"wifi_ssid\" value=\"{ssid}\" required>

    <label>Wi-Fi Password</label>
        <input type="password" name="wifi_password" value="{wifi_password}" required>

    <label>Backend IP (or host:port)</label>
    <input name=\"backend_host\" value=\"{backend}\" placeholder=\"192.168.1.42\" required>

    <button type=\"submit\">Save and Connect</button>
  </form>
</body>
</html>
""".format(status=status, ssid=ssid, wifi_password=wifi_password, backend=backend)


def setup_success_html(url):
    return """HTTP/1.1 200 OK\r
Content-Type: text/html\r
Connection: close\r
\r
<!DOCTYPE html>
<html>
<head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"></head>
<body style=\"font-family: Arial, sans-serif; max-width: 520px; margin: 24px auto;\">
  <h2>Saved</h2>
  <p>Configuration saved. Pico is now connecting to Wi-Fi.</p>
  <p>Backend URL: <strong>{}</strong></p>
  <p>You can close this page.</p>
</body>
</html>
""".format(url)


def run_setup_portal():
    stored = load_config()
    ap = start_access_point()
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)
    s.settimeout(1)

    status = "Submit Wi-Fi SSID, Wi-Fi password, and backend IP."

    try:
        while True:
            try:
                cl, _ = s.accept()
            except OSError:
                continue

            try:
                cl.settimeout(2)

                req = b""
                while b"\r\n\r\n" not in req and len(req) < 4096:
                    chunk = cl.recv(512)
                    if not chunk:
                        break
                    req += chunk

                if not req:
                    continue

                header_end = req.find(b"\r\n\r\n")
                if header_end < 0:
                    header = req.decode("utf-8", "ignore")
                    body = ""
                else:
                    header_bytes = req[:header_end]
                    body_bytes = req[header_end + 4:]
                    header = header_bytes.decode("utf-8", "ignore")

                    content_length = 0
                    for line in header.split("\r\n"):
                        lower = line.lower()
                        if lower.startswith("content-length:"):
                            try:
                                content_length = int(line.split(":", 1)[1].strip())
                            except Exception:
                                content_length = 0
                            break

                    while len(body_bytes) < content_length:
                        chunk = cl.recv(min(512, content_length - len(body_bytes)))
                        if not chunk:
                            break
                        body_bytes += chunk

                    body = body_bytes.decode("utf-8", "ignore")

                req_line = header.split("\r\n", 1)[0] if header else ""
                method = "GET"
                if req_line:
                    method = req_line.split(" ", 1)[0]

                if method == "POST":
                    form = parse_form_encoded(body)
                    cfg = {
                        "wifi_ssid": form.get("wifi_ssid", "").strip(),
                        "wifi_password": form.get("wifi_password", ""),
                        "backend_host": normalize_backend_host(form.get("backend_host", "")),
                    }
                    stored = cfg

                    if cfg["wifi_ssid"] and cfg["wifi_password"] and cfg["backend_host"]:
                        save_config(cfg)
                        url = build_backend_url(cfg["backend_host"])
                        cl.send(setup_success_html(url).encode("utf-8"))
                        print("Setup saved; leaving AP mode")
                        return cfg

                    status = "All fields are required: SSID, password, and backend IP."

                cl.send(setup_page_html(stored, status).encode("utf-8"))
            except Exception as exc:
                print("Setup portal error:", exc)
            finally:
                try:
                    cl.close()
                except Exception:
                    pass
    finally:
        try:
            s.close()
        except Exception:
            pass
        stop_access_point(ap)

def connect_wifi():
    global wlan
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not WIFI_SSID:
        print("No WiFi SSID configured")
        return wlan
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 15
        while not wlan.isconnected() and timeout > 0:
            import time
            time.sleep(1)
            timeout -= 1
    if wlan.isconnected():
        print("WiFi connected:", wlan.ifconfig()[0])
    else:
        print("WiFi connection failed — continuing without network")
    return wlan

# Set up some pin allocations for the Analogues and switches
va_pin = ADC(Pin(28))
vb_pin = ADC(Pin(26))
vpot_pin = ADC(Pin(27))
OL_CL_pin = Pin(12, Pin.IN, Pin.PULL_UP)
BU_BO_pin = Pin(2, Pin.IN, Pin.PULL_UP)

# Set up the I2C for the INA219 chip for current sensing
ina_i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=2400000)

# Some PWM settings, pin number, frequency, duty cycle limits and start with the PWM outputting the default of the min value.
pwm = PWM(Pin(9))
pwm.freq(100000)
min_pwm = 1000
max_pwm = 64536
pwm_out = min_pwm
pwm_ref = 30000

#Some error signals
trip = 0
OC = 0

# The potentiometer is prone to noise so we are filtering the value using a moving average
v_pot_filt = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
              0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
v_pot_index = 0

# Gains etc for the PID controller
i_ref = 0 # Voltage reference for the CL modes
i_err = 0 # Voltage error
i_err_int = 0 # Voltage error integral
i_pi_out = 0 # Output of the voltage PI controller
kp = 100 # Boost Proportional Gain
ki = 300 # Boost Integral Gain

# Basic signals to control logic flow
global timer_elapsed
timer_elapsed = 0
count = 0
first_run = 1

# Need to know the shunt resistance
global SHUNT_OHMS
SHUNT_OHMS = 0.10

latest_data = {
        "va": 0.0,
        "vb": 0.0,
        "vpot": 0.0,
        "iL": 0.0,
        "OC": 0,
        "CL": 0,
        "BU": 0,
        "duty": 0,
        "i_err": 0.0,
        "i_ref": 0.0
}


def dashboard_json(data):
        return (
                '{"va":%.3f,"vb":%.3f,"vpot":%.3f,"iL":%.3f,'
                '"OC":%d,"CL":%d,"BU":%d,"duty":%d,"i_err":%.3f,"i_ref":%.3f}'
        ) % (
                data["va"], data["vb"], data["vpot"], data["iL"],
                data["OC"], data["CL"], data["BU"], data["duty"],
                data["i_err"], data["i_ref"]
        )


def send_json(data):
    global wlan
    body = dashboard_json(data)
    for attempt in range(3):  # Increase retry attempts to 3
        try:
            if wlan is None or not wlan.isconnected():
                wlan = connect_wifi()
            if wlan is None or not wlan.isconnected():
                print("HTTP POST skipped: WiFi not connected")
                return

            r = urequests.post(
                BACKEND_URL,
                data=body,
                headers={"Content-Type": "application/json"},
            )
            r.close()
            return
        except Exception as e:
            print("HTTP POST failed:", e)
            return

# saturation function for anything you want saturated within bounds
def saturate(signal, upper, lower): 
    if signal > upper:
        signal = upper
    if signal < lower:
        signal = lower
    return signal

# This is the function executed by the loop timer, it simply sets a flag which is used to control the main loop
def tick(t): 
    global timer_elapsed
    timer_elapsed = 1

# These functions relate to the configuring of and reading data from the INA219 Current sensor
class ina219: 
    
    # Register Locations
    REG_CONFIG = 0x00
    REG_SHUNTVOLTAGE = 0x01
    REG_BUSVOLTAGE = 0x02
    REG_POWER = 0x03
    REG_CURRENT = 0x04
    REG_CALIBRATION = 0x05
    
    def __init__(self,sr, address, maxi):
        self.address = address
        self.shunt = sr
            
    def vshunt(icur):
        # Read Shunt register 1, 2 bytes
        reg_bytes = ina_i2c.readfrom_mem(icur.address, icur.REG_SHUNTVOLTAGE, 2)
        reg_value = int.from_bytes(reg_bytes, 'big')
        if reg_value > 2**15: #negative
            sign = -1
            for i in range(16): 
                reg_value = (reg_value ^ (1 << i))
        else:
            sign = 1
        return (float(reg_value) * 1e-5 * sign)
        
    def vbus(ivolt):
        # Read Vbus voltage
        reg_bytes = ina_i2c.readfrom_mem(ivolt.address, ivolt.REG_BUSVOLTAGE, 2)
        reg_value = int.from_bytes(reg_bytes, 'big') >> 3
        return float(reg_value) * 0.004
        
    def configure(conf):
        #ina_i2c.writeto_mem(conf.address, conf.REG_CONFIG, b'\x01\x9F') # PG = 1
        #ina_i2c.writeto_mem(conf.address, conf.REG_CONFIG, b'\x09\x9F') # PG = /2
        ina_i2c.writeto_mem(conf.address, conf.REG_CONFIG, b'\x19\x9F') # PG = /8
        ina_i2c.writeto_mem(conf.address, conf.REG_CALIBRATION, b'\x00\x00')


# Here we go, main function, always executes
cfg = run_setup_portal()
apply_network_config(cfg)
print("Using backend:", BACKEND_URL)
connect_wifi()

while True:
    if first_run:
        # for first run, set up the INA link and the loop timer settings
        ina = ina219(SHUNT_OHMS, 64, 5)
        ina.configure()

        first_run = 0
        
        # This starts a 1kHz timer which we use to control the execution of the control loops and sampling
        loop_timer = Timer(mode=Timer.PERIODIC, freq=1000, callback=tick)
    
    # If the timer has elapsed it will execute some functions, otherwise it skips everything and repeats until the timer elapses
    if timer_elapsed == 1: # This is executed at 1kHz
        va = 1.017*(12490/2490)*3.3*(va_pin.read_u16()/65536) # calibration factor * potential divider ratio * ref voltage * digital reading
        vb = 1.015*(12490/2490)*3.3*(vb_pin.read_u16()/65536) # calibration factor * potential divider ratio * ref voltage * digital reading
        
        vpot_in = 1.026*3.3*(vpot_pin.read_u16()/65536) # calibration factor * potential divider ratio * ref voltage * digital reading
        v_pot_filt[v_pot_index] = vpot_in # Adds the new reading to our array of readings at the current index
        v_pot_index = v_pot_index + 1 # Moves the index of the buffer for next time
        if v_pot_index == 100: # Loops it round if it reaches the end
            v_pot_index = 0
        vpot = sum(v_pot_filt)/100 # Actual reading used is the average of the last 100 readings
        
        Vshunt = ina.vshunt()
        CL = OL_CL_pin.value() # Are we in closed or open loop mode
        BU = BU_BO_pin.value() # Are we in buck or boost mode?
            
        # New min and max PWM limits and we use the measured current directly
        min_pwm = 0 
        max_pwm = 64536
        iL = Vshunt/SHUNT_OHMS
        pwm_ref = saturate(65536-(int((vpot/3.3)*65536)),max_pwm,min_pwm) # convert the pot value to a PWM value for use later
              
        if CL != 1: # Buck-OL Open loop so just limit the current but otherwise pass through the reference directly as a duty cycle
            i_err_int = 0 #reset integrator
            
            if iL > 2: # Current limiting function
                pwm_out = pwm_out - 10 # if there is too much current, knock down the duty cycle
                OC = 1 # Set the OC flag
                pwm_out = saturate(pwm_out, pwm_ref, min_pwm)
            elif iL < -2:
                pwm_out = pwm_out + 10 # We are now below the current limit so bring the duty back up
                OC = 1 # Reset the OC flag
                pwm_out = saturate(pwm_out, max_pwm, pwm_ref)
            else:
                pwm_out = pwm_ref
                OC = 0
                pwm_out = saturate(pwm_out, pwm_ref, min_pwm)
                
            duty = 65536-pwm_out # Invert the PWM because thats how it needs to be output for a buck because of other inversions in the hardware
            pwm.duty_u16(duty) # now we output the pwm
            
        else: # Closed Loop Current Control
                    
            i_ref = saturate(vpot-1.66, 1.5,-1.5)
            i_err = i_ref-iL # calculate the error in voltage
            i_err_int = i_err_int + i_err # add it to the integral error
            i_err_int = saturate(i_err_int, 10000, -10000) # saturate the integral error
            i_pi_out = (kp*i_err)+(ki*i_err_int) # Calculate a PI controller output
            
            pwm_out = saturate(i_pi_out,max_pwm,min_pwm) # Saturate that PI output
            duty = int(65536-pwm_out) # Invert because reasons
            pwm.duty_u16(duty) # Send the output of the PI controller out as PWM
            
        
        # Keep a count of how many times we have executed and reset the timer so we can go back to waiting
        count = count + 1
        timer_elapsed = 0
        
        # This set of prints executes every 100 loops by default and can be used to output debug or extra info over USB enable or disable lines as needed
        if count > 100:
            '''
            print("Va = {:.3f}".format(va))
            print("Vb = {:.3f}".format(vb))
            print("Vpot = {:.3f}".format(vpot))
            print("iL = {:.3f}".format(iL))
            print("OC = {:b}".format(OC))
            print("CL = {:b}".format(CL))
            print("BU = {:b}".format(BU))
            #print("trip = {:b}".format(trip))
            print("duty = {:d}".format(duty))
            print("i_err = {:.3f}".format(i_err))
            #print("i_err_int = {:.3f}".format(i_err_int))
            #print("i_pi_out = {:.3f}".format(i_pi_out))
            print("i_ref = {:.3f}".format(i_ref))
            #print("v_err = {:.3f}".format(v_err))
            #print("v_err_int = {:.3f}".format(v_err_int))
            #print("v_pi_out = {:.3f}".format(v_pi_out))
            #print(v_pot_filt)
            count = 0
            '''

        latest_data["va"] = va
        latest_data["vb"] = vb
        latest_data["vpot"] = vpot
        latest_data["iL"] = iL
        latest_data["OC"] = OC
        latest_data["CL"] = CL
        latest_data["BU"] = BU
        latest_data["duty"] = duty
        latest_data["i_err"] = i_err
        latest_data["i_ref"] = i_ref

        # Emit one JSON line at ~10 Hz over USB serial.
        if count % 100 == 0:
            send_json(latest_data)
