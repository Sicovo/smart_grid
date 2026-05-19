import json
import os
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc
from db import SessionLocal, GridSnapshot, SMPSnapshot, init_db, save_smps_snapshot

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
                            save_smps_snapshot(payload)
                        except (ValueError, KeyError, TypeError):
                            continue
            except Exception as exc:
                print("SMPS ingest reconnecting after error: {}".format(exc))

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


@app.on_event("startup")
def startup_event():
    init_db(reset=True)
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
    }


@app.get("/smps/snapshots")
def get_smps_snapshots(limit: int = 120):
    db = SessionLocal()

    rows = (
        db.query(SMPSnapshot)
        .order_by(desc(SMPSnapshot.id))
        .limit(limit)
        .all()
    )

    db.close()

    return [
        {
            "id": row.id,
            "timestamp": row.timestamp.isoformat(),
            "va": row.va,
            "vb": row.vb,
            "vpot": row.vpot,
            "iL": row.iL,
            "OC": row.OC,
            "CL": row.CL,
            "BU": row.BU,
            "duty": row.duty,
            "i_err": row.i_err,
            "i_ref": row.i_ref,
        }
        for row in reversed(rows)
    ]


@app.post("/smps/ingest")
async def ingest_smps(payload: dict):
    try:
        save_smps_snapshot(payload)
    except (KeyError, TypeError) as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=str(exc))
    return {"ok": True}


@app.get("/smps/latest")
def get_smps_latest():
    db = SessionLocal()

    row = (
        db.query(SMPSnapshot)
        .order_by(desc(SMPSnapshot.id))
        .first()
    )

    db.close()

    if row is None:
        return {"error": "No SMPS snapshots yet"}

    return {
        "id": row.id,
        "timestamp": row.timestamp.isoformat(),
        "va": row.va,
        "vb": row.vb,
        "vpot": row.vpot,
        "iL": row.iL,
        "OC": row.OC,
        "CL": row.CL,
        "BU": row.BU,
        "duty": row.duty,
        "i_err": row.i_err,
        "i_ref": row.i_ref,
    }