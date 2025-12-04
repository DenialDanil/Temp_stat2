from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Список усіх вимірювань
dani = []

@app.get("/")
async def root():
    return {"message": "Temp_stat працює!"}

@app.post("/data")
async def receive(temp: float, hum: float):
    item = {
        "temp": round(temp, 1),
        "hum": round(hum, 1),
        "time": datetime.now().strftime("%H:%M:%S")
    }
    dani.append(item)
    # Зберігаємо максимум 500 точок
    if len(dani) > 500:
        dani.pop(0)
    print("Отримано:", item)
    return {"status": "ok"}

@app.get("/data")
async def last():
    return dani[-1] if dani else {"temp": 0.0, "hum": 0.0, "time": "—"}

@app.get("/history")
async def history():
    return dani[::-1] if dani else []
