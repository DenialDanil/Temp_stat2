from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Останні дані (стартові значення, щоб не було порожньо)
latest = {"temp": 0.0, "hum": 0.0, "time": "—"}

@app.get("/")
async def root():
    return {"message": "Temp_stat працює!"}

@app.get("/data")
async def get_data():
    return latest  # завжди повертає останнє значення

@app.post("/data")
async def receive(temp: float = 0.0, hum: float = 0.0):
    global latest
    latest = {
        "temp": round(temp, 1),
        "hum": round(hum, 1),
        "time": datetime.now().strftime("%H:%M:%S")
    }
    print("Отримано:", latest)
    return {"status": "ok"}
