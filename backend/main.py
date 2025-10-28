# backend/main.py
import os
import ssl
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import text, create_engine, Column, Integer, String, select
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
from sqlalchemy.engine import make_url

def truthy(x) -> bool:
    return str(x).lower() in {"1", "true", "yes", "on"}

app = FastAPI()

db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise RuntimeError("DATABASE_URL not set")

# Ensure SQLAlchemy uses the PyMySQL driver
if db_url.startswith("mysql://"):
    db_url = "mysql+pymysql://" + db_url[len("mysql://"):]

# Extract TLS/SSL params from the query string so they don't become unknown kwargs
u = urlparse(db_url)
q = dict(parse_qsl(u.query, keep_blank_values=True))

ssl_requested = truthy(q.pop("tls", False)) or truthy(q.pop("ssl", False))
ssl_ca   = q.pop("ssl_ca",   None) or os.getenv("MYSQL_SSL_CA")    # optional
ssl_cert = q.pop("ssl_cert", None) or os.getenv("MYSQL_SSL_CERT")  # optional client cert
ssl_key  = q.pop("ssl_key",  None) or os.getenv("MYSQL_SSL_KEY")   # optional client key

connect_args = {}
if ssl_ca or ssl_cert or ssl_key:
    ctx = ssl.create_default_context(cafile=ssl_ca)
    if ssl_cert and ssl_key:
        ctx.load_cert_chain(certfile=ssl_cert, keyfile=ssl_key)
    connect_args["ssl"] = ctx
elif ssl_requested:
    # Encrypt without CA verification if only tls=true/ssl=true was provided.
    # Prefer providing MYSQL_SSL_CA (RDS CA bundle) in production.
    connect_args["ssl"] = {}

# Rebuild a clean URL without the unsupported tls/ssl params
clean_url = urlunparse(u._replace(query=urlencode(q, doseq=True)))

engine = create_engine(clean_url, pool_pre_ping=True, future=True, connect_args=connect_args)
try:
    with engine.connect() as _:
        pass
except OperationalError as e:
    # MySQL 1049 = Unknown database
    if getattr(e.orig, "args", [None])[0] == 1049:
        url = make_url(clean_url)
        dbname = url.database
        # connect without a database, then create it
        tmp = create_engine(url.set(database=None), pool_pre_ping=True, future=True, connect_args=connect_args)
        with tmp.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{dbname}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        tmp.dispose()
        engine.dispose()
        engine = create_engine(clean_url, pool_pre_ping=True, future=True, connect_args=connect_args)
    else:
        raiseSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
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
