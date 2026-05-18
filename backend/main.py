from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc
from db import SessionLocal, GridSnapshot

app = FastAPI()

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