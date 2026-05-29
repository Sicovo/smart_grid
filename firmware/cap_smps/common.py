# common.py — shared scaffolding for all SMPS firmware on the smart-grid project.
#
# Copy this file to every Pico W alongside its role file (pv_smps.py, grid_smps.py,
# export_smps.py, led_load.py) and wifi_config.py.
#
# What's in here:
#   - PI controller class (matches the shape of the inline PI in SMPS_2026_Bidirectional.py)
#   - INA219 driver (lifted from SMPS_2026_Bidirectional.py, repackaged as a class)
#   - WiFi connect helper
#   - Minimal HTTP server that runs on core 1 via _thread, so the 1 kHz control
#     loop on core 0 is NEVER blocked by network I/O
#   - Shared safety constants and watchdog helper
#
# Design rule: the timer-driven control loop on core 0 never touches the network.
# It only reads state["cmd"] and writes state["tlm"]. If WiFi dies, the inner PI
# keeps tracking the last commanded i_ref. After WATCHDOG_S seconds with no
# commands, the role file is expected to force i_ref=0 (safe state).

import network, socket, json, time, _thread, gc
from machine import Pin, ADC, I2C

# Pull WiFi creds from a separate file so they don't get committed.
try:
    from wifi_config import WIFI_SSID, WIFI_PASS, STATIC_IP, SUBNET, GATEWAY, DNS
except ImportError:
    WIFI_SSID = ""
    WIFI_PASS = ""
    STATIC_IP = None
    SUBNET = "255.255.255.0"
    GATEWAY = "192.168.137.1"
    DNS = "192.168.137.1"

# ---------------- Tuning constants shared across all role files ----------------

PWM_FREQ_HZ      = 100_000
PWM_MIN          = 1000
PWM_MAX          = 64536
VB_HI_TRIP       = 13.0      # bus over-volt → latched trip on bus-facing modules
VB_LO_TRIP       = 4.0       # bus under-volt → latched trip (4 V is below any LED Vf)
I_TRIP_ABS       = 2.8       # |iL| trip on bidirectional modules
WATCHDOG_S       = 10.0      # no /cmd POST in this long → force safe defaults
TICK_HZ          = 1000


# ---------------- PI controller ----------------
# Same math as the inline PI in SMPS_2026_Bidirectional.py:
#     integ += err
#     u = kp*err + ki*integ
#     u, integ both saturated.
# Wrapping it in a class so each module can have several independent PIs
# (e.g. grid has an outer voltage PI plus an inner current PI) without
# accidentally cross-contaminating their integrators.

class PI:
    def __init__(self, kp, ki, out_lo, out_hi, i_lo=-10000.0, i_hi=10000.0):
        self.kp = kp
        self.ki = ki
        self.lo = out_lo
        self.hi = out_hi
        self.i_lo = i_lo
        self.i_hi = i_hi
        self.integ = 0.0

    def reset(self):
        self.integ = 0.0

    def step(self, err):
        self.integ += err
        if self.integ > self.i_hi:
            self.integ = self.i_hi
        elif self.integ < self.i_lo:
            self.integ = self.i_lo
        u = self.kp * err + self.ki * self.integ
        if u > self.hi:
            u = self.hi
        elif u < self.lo:
            u = self.lo
        return u


def saturate(x, hi, lo):
    if x > hi:
        return hi
    if x < lo:
        return lo
    return x


# ---------------- INA219 current sensor ----------------
# Repackaged from SMPS_2026_Bidirectional.py. Configured for PG=/8 (±320 mV
# shunt range) and zero calibration register (we read shunt voltage directly
# and divide by the shunt resistance ourselves).

class INA219:
    REG_CONFIG       = 0x00
    REG_SHUNTVOLTAGE = 0x01
    REG_BUSVOLTAGE   = 0x02
    REG_CALIBRATION  = 0x05

    def __init__(self, i2c, address=0x40, shunt_ohms=0.10):
        self.i2c = i2c
        self.address = address
        self.shunt = shunt_ohms
        # PG=/8 — matches the bidirectional template
        self.i2c.writeto_mem(self.address, self.REG_CONFIG, b'\x19\x9F')
        self.i2c.writeto_mem(self.address, self.REG_CALIBRATION, b'\x00\x00')

    def vshunt(self):
        raw = self.i2c.readfrom_mem(self.address, self.REG_SHUNTVOLTAGE, 2)
        v = int.from_bytes(raw, 'big')
        if v > 2 ** 15:
            sign = -1
            for i in range(16):
                v ^= (1 << i)
        else:
            sign = 1
        return float(v) * 1e-5 * sign

    def iL(self):
        return self.vshunt() / self.shunt


# ---------------- WiFi ----------------

def wifi_connect(hostname, timeout_ms=15000):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if STATIC_IP:
        wlan.ifconfig((STATIC_IP, SUBNET, GATEWAY, DNS))

    try:
        wlan.config(hostname=hostname)
    except (OSError, ValueError):
        pass

    wlan.connect(WIFI_SSID, WIFI_PASS)

    deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
    while not wlan.isconnected() and time.ticks_diff(deadline, time.ticks_ms()) > 0:
        time.sleep_ms(200)

    return wlan


# ---------------- HTTP server (runs on core 1) ----------------
#
# Hand-rolled because MicroPython has no batteries-included HTTP server and
# we don't want to add a dependency for one. ~50 lines.
#
# Endpoints:
#   GET  /tlm   → returns state["tlm"] as JSON
#   POST /cmd   → JSON body merged into state["cmd"]; bumps last_cmd_ms
#
# Threading rules:
#   - This function runs on core 1 via _thread.start_new_thread().
#   - It only touches state["cmd"], state["tlm"], state["last_cmd_ms"].
#   - Dict updates on these keys are atomic enough in MicroPython for our
#     coarse setpoints (1 reader/1 writer per field, no read-modify-write).
#   - Never call anything that touches PWM, ADC, or INA219 from here.

# CORS headers so dashboard.html can talk to us from a file:// origin.
CORS = (b'Access-Control-Allow-Origin: *\r\n'
        b'Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n'
        b'Access-Control-Allow-Headers: Content-Type\r\n')


def _sendall(sock, data):
    try:
        sock.sendall(data)
        return
    except Exception:
        pass
    mv = memoryview(data)
    sent = 0
    while sent < len(data):
        n = sock.send(mv[sent:])
        if n is None or n <= 0:
            break
        sent += n


def _serve_dashboard_html(sock):
    # Stream file in chunks; avoids RAM spikes and truncated socket writes.
    for p in ('dashboard.html', '/dashboard.html', 'index.html', '/index.html'):
        try:
            _sendall(sock, b'HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n' + CORS +
                     b'Connection: close\r\n\r\n')
            with open(p, 'rb') as f:
                while True:
                    chunk = f.read(1024)
                    if not chunk:
                        break
                    _sendall(sock, chunk)
            return True
        except Exception:
            pass
    return False


def _http_server(state, port):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', port))
    s.listen(2)
    s.settimeout(0.5)   # accept() returns every 500 ms so we can re-check state['shutdown']
    gc_count = 0
    while not state.get('shutdown', False):
        cl = None
        try:
            cl, _addr = s.accept()
            cl.settimeout(2.0)
            req = cl.recv(2048)
            if not req:
                cl.close()
                continue
            first = req.split(b'\r\n', 1)[0]
            parts = first.split(b' ')
            if len(parts) < 2:
                cl.close()
                continue
            method, path = parts[0], parts[1]

            if method == b'OPTIONS':
                cl.send(b'HTTP/1.1 204 No Content\r\n' + CORS +
                        b'Content-Length: 0\r\nConnection: close\r\n\r\n')
            elif method == b'GET' and (path == b'/' or path == b'/dashboard.html' or path == b'/index.html'):
                if not _serve_dashboard_html(cl):
                    body = (b'<html><body><h3>dashboard.html not found</h3>'
                            b'<p>Upload dashboard.html to the Pico filesystem.</p></body></html>')
                    _sendall(cl, b'HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n' + CORS +
                             b'Content-Length: ' + str(len(body)).encode() +
                             b'\r\nConnection: close\r\n\r\n' + body)
            elif method == b'GET' and path == b'/tlm':
                body = json.dumps(state['tlm']).encode()
                _sendall(cl, b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n' + CORS +
                         b'Content-Length: ' + str(len(body)).encode() +
                         b'\r\nConnection: close\r\n\r\n' + body)
            elif method == b'POST' and path == b'/cmd':
                idx = req.find(b'\r\n\r\n')
                body = req[idx + 4:] if idx >= 0 else b''
                try:
                    cmd = json.loads(body)
                    if isinstance(cmd, dict):
                        state['cmd'].update(cmd)
                        state['last_cmd_ms'] = time.ticks_ms()
                        _sendall(cl, b'HTTP/1.1 200 OK\r\n' + CORS +
                                 b'Content-Length: 2\r\nConnection: close\r\n\r\nOK')
                    else:
                        raise ValueError('not a JSON object')
                except Exception as e:
                    err = ('{"err":"%s"}' % str(e)).encode()
                    _sendall(cl, b'HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\n' + CORS +
                             b'Content-Length: ' + str(len(err)).encode() +
                             b'\r\nConnection: close\r\n\r\n' + err)
            else:
                _sendall(cl, b'HTTP/1.1 404 Not Found\r\n' + CORS +
                         b'Content-Length: 0\r\nConnection: close\r\n\r\n')
        except Exception:
            pass
        finally:
            if cl is not None:
                try:
                    cl.close()
                except Exception:
                    pass
            # Collect every few requests, not every one. At the cap cycle
            # test's 20 Hz logging, a per-request stop-the-world GC stalls
            # this WiFi/HTTP thread ~20x/s and makes the link shaky.
            gc_count += 1
            if gc_count >= 10:
                gc_count = 0
                gc.collect()
    # Loop exited (state['shutdown'] is True). Release the listening socket.
    try:
        s.close()
    except Exception:
        pass


def start_http_thread(state, port=80):
    state.setdefault('shutdown', False)
    _thread.start_new_thread(_http_server, (state, port))


# ---------------- Watchdog ----------------

def watchdog_tripped(state, now_ms):
    return time.ticks_diff(now_ms, state['last_cmd_ms']) > int(WATCHDOG_S * 1000)
