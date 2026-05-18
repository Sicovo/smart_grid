import time
import requests
from pprint import pprint

BASE_URL = "https://icelec50015.azurewebsites.net"

def get_json(endpoint):
    url = BASE_URL + endpoint
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    return r.json()

def build_state():
    sun = get_json("/sun")
    price = get_json("/price")
    demand = get_json("/demand")
    deferables = get_json("/deferables")

    state = {
        "tick": demand["tick"],

        # environment
        "sun": sun["sun"],

        # market
        "buy_price": price["buy_price"],
        "sell_price": price["sell_price"],

        # load
        "instant_demand": demand["demand"],
        "deferables": deferables,
    }

    return state

if __name__ == "__main__":
    while True:
        try:
            state = build_state()

            print("\n=== CURRENT GRID STATE ===")
            pprint(state)

        except Exception as e:
            print("ERROR:", e)

        time.sleep(5)