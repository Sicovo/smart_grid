# wifi_config.example.py — template for STA modules joining cap AP.
#
#     cp firmware/wifi_config.example.py firmware/wifi_config.py
#
# The real wifi_config.py is gitignored so credentials don't end up on GitHub.

WIFI_SSID = "SmartGrid-Cap"
WIFI_PASS = "smartgrid123"
BACKEND_URL = "http://172.20.10.2:8000/smps/ingest"
