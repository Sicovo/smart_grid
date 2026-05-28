# wifi_config.py — fill in your hotspot credentials and copy to each Pico W.
#
# Kept in a separate file so it's easy to git-ignore. The README warns that the
# college WiFi is hard to use with embedded devices, so this is expected to
# point at a phone hotspot.

WIFI_SSID = "PICO_AP"
WIFI_PASS = "12345688"

STATIC_IP = "192.168.137.22"
SUBNET = "255.255.255.0"
GATEWAY = "192.168.137.1"
DNS = "192.168.137.1"