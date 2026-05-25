import time
import requests
from pprint import pprint
from db import init_db, save_snapshot, save_smps_snapshot

AZURE_BASE_URL = "https://icelec50015.azurewebsites.net"
PICO_BASE_URL = "http://192.168.4.1:8000"

def get_json(url):
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    return r.json()

def build_grid_state():
    sun = get_json(AZURE_BASE_URL + "/sun")
    price = get_json(AZURE_BASE_URL + "/price")
    demand = get_json(AZURE_BASE_URL + "/demand")
    deferables = get_json(AZURE_BASE_URL + "/deferables")

    state = {
        "tick": demand["tick"],
        "sun": sun["sun"],
        "buy_price": price["buy_price"],
        "sell_price": price["sell_price"],
        "instant_demand": demand["demand"],
        "deferables": deferables,
    }

    return state


def fetch_smps_state():
    payload = get_json(PICO_BASE_URL + "/smps/latest")
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
    print("SMPS source:", PICO_BASE_URL)

    while True:
        try:
            grid_state = build_grid_state()
            save_snapshot(grid_state)

            print("\n=== SAVED GRID STATE ===")
            pprint(grid_state)

            smps_state = fetch_smps_state()
            save_smps_snapshot(smps_state)

            print("=== SAVED SMPS STATE ===")
            pprint(smps_state)

        except Exception as e:
            print("ERROR:", e)

        time.sleep(5)