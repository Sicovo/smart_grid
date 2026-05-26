import os
import time
import requests
from pprint import pprint
from db import init_db, save_snapshot, save_smps_snapshot

AZURE_BASE_URL = "https://icelec50015.azurewebsites.net"
PICO_BASE_URL = os.getenv("PICO_BASE_URL", "").strip()
REQUEST_TIMEOUT = float(os.getenv("POLL_REQUEST_TIMEOUT", "5"))

def get_json(url):
    r = requests.get(url, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()

def build_grid_state():
    try:
        sun = get_json(AZURE_BASE_URL + "/sun")
        price = get_json(AZURE_BASE_URL + "/price")
        demand = get_json(AZURE_BASE_URL + "/demand")
        deferables = get_json(AZURE_BASE_URL + "/deferables")
    except requests.RequestException as exc:
        print("Grid source unavailable: {}".format(exc))
        return None

    state = {
        "day": demand["day"],
        "tick": demand["tick"],
        "sun": sun["sun"],
        "buy_price": price["buy_price"],
        "sell_price": price["sell_price"],
        "instant_demand": demand["demand"],
        "deferables": deferables,
    }

    return state


def fetch_smps_state():
    if not PICO_BASE_URL:
        return None

    try:
        payload = get_json(PICO_BASE_URL + "/smps/latest")
    except requests.RequestException as exc:
        print("SMPS source unavailable: {}".format(exc))
        return None

    required_fields = [
        "va", "vb", "vpot", "iL", "OC", "CL", "BU", "duty", "i_err", "i_ref"
    ]
    for key in required_fields:
        if key not in payload:
            raise KeyError("Missing SMPS field: {}".format(key))
    return payload

if __name__ == "__main__":
    init_db()
    print("Grid source:", AZURE_BASE_URL)
    if PICO_BASE_URL:
        print("SMPS source:", PICO_BASE_URL)
    else:
        print("SMPS polling disabled (set PICO_BASE_URL to enable)")

    while True:
        try:
            grid_state = build_grid_state()
            if grid_state is not None:
                save_snapshot(grid_state)

                print("\n=== SAVED GRID STATE ===")
                pprint(grid_state)

        except Exception as e:
            print("ERROR:", e)

        try:
            smps_state = fetch_smps_state()
            if smps_state is not None:
                save_smps_snapshot(smps_state)

                print("=== SAVED SMPS STATE ===")
                pprint(smps_state)
        except Exception as e:
            print("ERROR:", e)

        time.sleep(1)