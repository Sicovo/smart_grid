from sqlalchemy import create_engine, Column, Integer, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///smartgrid.db"

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

class GridSnapshot(Base):
    __tablename__ = "grid_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    tick = Column(Integer)
    sun = Column(Float)
    buy_price = Column(Float)
    sell_price = Column(Float)
    instant_demand = Column(Float)


class SMPSnapshot(Base):
    __tablename__ = "smps_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    va = Column(Float)
    vb = Column(Float)
    vpot = Column(Float)
    iL = Column(Float)
    OC = Column(Integer)
    CL = Column(Integer)
    BU = Column(Integer)
    duty = Column(Integer)
    i_err = Column(Float)
    i_ref = Column(Float)

def init_db():
    Base.metadata.create_all(bind=engine)

def save_snapshot(state):
    db = SessionLocal()

    snapshot = GridSnapshot(
        tick=state["tick"],
        sun=state["sun"],
        buy_price=state["buy_price"],
        sell_price=state["sell_price"],
        instant_demand=state["instant_demand"],
    )

    db.add(snapshot)
    db.commit()
    db.close()


def save_smps_snapshot(state):
    db = SessionLocal()

    snapshot = SMPSnapshot(
        va=state["va"],
        vb=state["vb"],
        vpot=state["vpot"],
        iL=state["iL"],
        OC=state["OC"],
        CL=state["CL"],
        BU=state["BU"],
        duty=state["duty"],
        i_err=state["i_err"],
        i_ref=state["i_ref"],
    )

    db.add(snapshot)
    db.commit()
    db.close()