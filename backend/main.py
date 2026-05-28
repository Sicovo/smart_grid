import json
import os
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc
from db import (SessionLocal, GridSnapshot, ModuleSnapshot,
                init_db, save_module_snapshot)

app = FastAPI()


def start_smps_serial_ingest():
    port = os.getenv("SMPS_SERIAL_PORT")
    if not port:
        print("SMPS ingest disabled: set SMPS_SERIAL_PORT (example: COM5)")
        return

    baud = int(os.getenv("SMPS_SERIAL_BAUD", "115200"))

    def worker():
        try:
            import serial
        except ImportError:
            print("SMPS ingest disabled: pyserial not installed (pip install pyserial)")
            return

        while True:
            try:
                with serial.Serial(port, baud, timeout=1) as ser:
                    print("SMPS ingest listening on {} @ {}".format(port, baud))
                    while True:
                        raw = ser.readline()
                        if not raw:
                            continue
                        try:
                            line = raw.decode("utf-8").strip()
                        except UnicodeError:
                            continue
                        if not line or not line.startswith("{"):
                            continue
                        try:
                            payload = json.loads(line)
                            if "role" in payload:
                                save_module_snapshot(payload)
                            else:
                                print("SMPS ingest ignored: payload missing role")
                        except (ValueError, KeyError, TypeError):
                            continue
            except Exception as exc:
                print("SMPS ingest reconnecting after error: {}".format(exc))

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


@app.on_event("startup")
def startup_event():
    init_db()
    start_smps_serial_ingest()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Smart Grid Backend is running"}

@app.get("/snapshots")
def get_snapshots(limit: int = 50):
    db = SessionLocal()

    rows = (
        db.query(GridSnapshot)
        .order_by(desc(GridSnapshot.id))
        .limit(limit)
        .all()
    )

    db.close()

    return [
        {
            "id": row.id,
            "timestamp": row.timestamp.isoformat(),
            "tick": row.tick,
            "sun": row.sun,
            "buy_price": row.buy_price,
            "sell_price": row.sell_price,
            "instant_demand": row.instant_demand,
            "deferables": json.loads(row.deferables_json or "[]"),
        }
        for row in reversed(rows)
    ]

@app.get("/latest")
def get_latest():
    db = SessionLocal()

    row = (
        db.query(GridSnapshot)
        .order_by(desc(GridSnapshot.id))
        .first()
    )

    db.close()

    if row is None:
        return {"error": "No snapshots yet"}

    return {
        "id": row.id,
        "timestamp": row.timestamp.isoformat(),
        "tick": row.tick,
        "sun": row.sun,
        "buy_price": row.buy_price,
        "sell_price": row.sell_price,
        "instant_demand": row.instant_demand,
        "deferables": json.loads(row.deferables_json or "[]"),
    }


@app.post("/smps/ingest")
async def ingest_smps(payload: dict):
    try:
        if "role" in payload:
            save_module_snapshot(payload)
        else:
            raise KeyError("Missing role field")
    except (KeyError, TypeError) as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=str(exc))
    return {"ok": True}


def _module_row_dict(row):
    return {
        "id":          row.id,
        "timestamp":   row.timestamp.isoformat(),
        "role":        row.role,
        "trip":        row.trip,
        "trip_reason": row.trip_reason,
        "enable":      row.enable,
        "wd":          row.wd,
        "pwm":         row.pwm,
        "vb_bus":      row.vb_bus,
        "iL":          row.iL,
        "i_ref":       row.i_ref,
        "vb_target":   row.vb_target,
        "v_panel":     row.v_panel,
        "p_panel":     row.p_panel,
        "vmpp_target": row.vmpp_target,
        "mppt_mode":   row.mppt_mode,
        "irradiance":  row.irradiance,
        "web_tick":    row.web_tick,
        "v_psu":       row.v_psu,
        "p_import":    row.p_import,
        "v_resistor":  row.v_resistor,
        "p_dissip":    row.p_dissip,
        "v_cap":       row.v_cap,
        "p_cap":       row.p_cap,
        "soc_pct":     row.soc_pct,
        "energy_J":    row.energy_J,
        "i_cmd":       row.i_cmd,
        "i_cmd_eff":   row.i_cmd_eff,
        "i_red":       row.i_red,
        "i_yel":       row.i_yel,
        "i_grn":       row.i_grn,
        "v_red":       row.v_red,
        "v_yel":       row.v_yel,
        "v_grn":       row.v_grn,
        "p_red":       row.p_red,
        "p_yel":       row.p_yel,
        "p_grn":       row.p_grn,
        "v_ldr":       row.v_ldr,
        "v_dark":      row.v_dark,
        "v_full":      row.v_full,
        "calibrated":  row.calibrated,
    }


@app.get("/modules/latest")
def get_all_modules_latest():
    db = SessionLocal()
    result = {}
    for role in ['pv', 'grid', 'export', 'cap', 'led', 'lux']:
        row = (
            db.query(ModuleSnapshot)
            .filter(ModuleSnapshot.role == role)
            .order_by(desc(ModuleSnapshot.id))
            .first()
        )
        result[role] = _module_row_dict(row) if row else None
    db.close()
    return result


@app.get("/modules/latest/{role}")
def get_module_latest(role: str):
    db = SessionLocal()
    row = (
        db.query(ModuleSnapshot)
        .filter(ModuleSnapshot.role == role)
        .order_by(desc(ModuleSnapshot.id))
        .first()
    )
    db.close()
    if row is None:
        return {"error": f"No snapshots for role {role}"}
    return _module_row_dict(row)


@app.get("/modules/snapshots/{role}")
def get_module_snapshots(role: str, limit: int = 60):
    db = SessionLocal()
    rows = (
        db.query(ModuleSnapshot)
        .filter(ModuleSnapshot.role == role)
        .order_by(desc(ModuleSnapshot.id))
        .limit(limit)
        .all()
    )
    db.close()
    return [_module_row_dict(r) for r in reversed(rows)]


