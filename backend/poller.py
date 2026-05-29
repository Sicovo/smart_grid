import os
import time
import requests
from pprint import pprint
from db import init_db, save_snapshot, save_module_snapshot
from concurrent.futures import ThreadPoolExecutor

AZURE_BASE_URL = "https://icelec50015.azurewebsites.net"
REQUEST_TIMEOUT = float(os.getenv("POLL_REQUEST_TIMEOUT", "5"))
MODULE_POLL_INTERVAL = float(os.getenv("MODULE_POLL_INTERVAL", "1"))

PICO_MODULE_URLS = {
    # "pv": "http://192.168.137.21",
    # "grid": "http://192.168.137.22",
    # "cap": "http://192.168.137.23",
    # "led": "http://192.168.137.24",
    # "export": "http://192.168.137.25",
}
MODULE_ROLES = [role for role, url in PICO_MODULE_URLS.items() if url]


def get_json(url):
    r = requests.get(url, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def build_grid_state_from_demand(demand):
    urls = {
        "sun": AZURE_BASE_URL + "/sun",
        "price": AZURE_BASE_URL + "/price",
        "deferables": AZURE_BASE_URL + "/deferables",
    }

    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {name: ex.submit(get_json, url) for name, url in urls.items()}
        results = {name: fut.result() for name, fut in futures.items()}

    sun = results["sun"]
    price = results["price"]
    deferables = results["deferables"]

    return {
        "day": demand["day"],
        "tick": demand["tick"],
        "sun": sun["sun"],
        "buy_price": price["buy_price"],
        "sell_price": price["sell_price"],
        "instant_demand": demand["demand"],
        "deferables": deferables,
    }


def fetch_module_state(role, base_url):
    if not base_url:
        return None
    try:
        return get_json(base_url.rstrip("/") + "/tlm")
    except requests.RequestException as exc:
        print(f"{role.upper()} source unavailable: {exc}")
        return None
    except ValueError as exc:
        print(f"{role.upper()} returned invalid JSON: {exc}")
        return None


def save_module_state(role, payload):
    if not payload:
        return False

    if not isinstance(payload, dict):
        print(f"{role.upper()} payload is not a JSON object")
        return False

    if "role" not in payload:
        payload["role"] = role
    elif payload["role"] != role:
        print(f"{role.upper()} payload role mismatch: expected {role}, got {payload['role']}")
        payload["role"] = role

    try:
        save_module_snapshot(payload)
        return True
    except Exception as exc:
        print(f"Failed to save module snapshot for {role}: {exc}")
        return False


def poll_all_modules():
    if not MODULE_ROLES:
        return

    with ThreadPoolExecutor(max_workers=len(MODULE_ROLES)) as ex:
        futures = {
            role: ex.submit(fetch_module_state, role, PICO_MODULE_URLS[role])
            for role in MODULE_ROLES
        }
        for role, fut in futures.items():
            payload = fut.result()
            if payload is None:
                continue
            if save_module_state(role, payload):
                print(f"=== SAVED MODULE STATE ({role}) ===")
                pprint(payload)


if __name__ == "__main__":
    init_db()
    print("Grid source:", AZURE_BASE_URL)
    print("Module polling enabled for:", MODULE_ROLES if MODULE_ROLES else "none")

    last_day = None
    last_tick = None

    while True:
        try:
            demand = get_json(AZURE_BASE_URL + "/demand")

            day = demand["day"]
            tick = demand["tick"]

            if (day, tick) != (last_day, last_tick):
                grid_state = build_grid_state_from_demand(demand)
                saved = save_snapshot(grid_state)

                if saved:
                    print("\n=== SAVED GRID STATE ===")
                    pprint(grid_state)

                last_day, last_tick = day, tick

        except Exception as e:
            print("GRID ERROR:", e)

        poll_all_modules()
        time.sleep(MODULE_POLL_INTERVAL)
