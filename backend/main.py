import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, select
from sqlalchemy.orm import sessionmaker, declarative_base

app = FastAPI()

db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise RuntimeError("DATABASE_URL not set")

# If URL uses 'mysql://', tell SQLAlchemy to use PyMySQL driver
if db_url.startswith("mysql://"):
    db_url = "mysql+pymysql://" + db_url[len("mysql://"):]

engine = create_engine(db_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

class Item(Base):
    __tablename__ = "demo_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(String(255), unique=True, nullable=False)

# Ensure table exists
Base.metadata.create_all(engine)

class ItemIn(BaseModel):
    value: str

@app.get("/api/items")
def list_items():
    with SessionLocal() as s:
        rows = s.execute(select(Item)).scalars().all()
        return {"items": [r.value for r in rows]}

@app.post("/api/items", status_code=201)
def add_item(payload: ItemIn):
    v = payload.value.strip()
    if not v:
        raise HTTPException(400, "value is empty")
    with SessionLocal() as s:
        # ignore duplicates gracefully
        if s.execute(select(Item).where(Item.value == v)).scalar_one_or_none():
            return {"status": "exists", "value": v}
        s.add(Item(value=v))
        s.commit()
        return {"status": "added", "value": v}

@app.delete("/api/items/{value}")
def remove_item(value: str):
    with SessionLocal() as s:
        row = s.execute(select(Item).where(Item.value == value)).scalar_one_or_none()
        if not row:
            raise HTTPException(404, "not found")
        s.delete(row)
        s.commit()
        return {"status": "deleted", "value": value}
