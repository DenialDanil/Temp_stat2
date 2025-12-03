from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import databases, sqlalchemy
from datetime import datetime

DATABASE_URL = "postgresql://postgres:твій_пароль@твій_хост:5432/postgres"  # Render дасть сам

database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

measurements = sqlalchemy.Table("measurements", metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("temp", sqlalchemy.Float),
    sqlalchemy.Column("hum", sqlalchemy.Float),
    sqlalchemy.Column("relay", sqlalchemy.Integer, default=0),
    sqlalchemy.Column("timestamp", sqlalchemy.DateTime, default=datetime.utcnow),
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])

@app.on_event("startup")
async def startup():
    await database.connect()
    await database.execute("CREATE TABLE IF NOT EXISTS measurements (id SERIAL PRIMARY KEY, temp FLOAT, hum FLOAT, relay INT DEFAULT 0, timestamp TIMESTAMPTZ DEFAULT NOW())")

@app.post("/data")
async def save(temp: float, hum: float, relay: int = 0):
    query = measurements.insert().values(temp=temp, hum=hum, relay=relay)
    await database.execute(query)
    return {"status": "saved"}

@app.get("/history")
async def history():
    query = "SELECT temp, hum, relay, timestamp FROM measurements ORDER BY timestamp DESC LIMIT 1000"
    rows = await database.fetch_all(query)
    return [{"temp": r[0], "hum": r[1], "relay": r[2], "ts": r[3].isoformat()} for r in rows]
