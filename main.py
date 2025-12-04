from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Сюди пишуться всі дані
history = []

# Завжди є хоча б одне значення
@app.get("/data")
async def last():
    if history:
        return history[-1]
    else:
        return {"temp": 0.0, "hum": 0.0, "time": "—"}

@app.post("/data")
async def receive(temp: float = 0.0, hum: float = 0.0):
    item = {
        "temp": round(float(temp), 1),
        "hum": round(float(hum), 1),
        "time": datetime.now().strftime("%H:%M:%S")
    }
    history.append(item)
    if len(history) > 500:
        history.pop(0)
    print("Отримано:", item)
    return {"status": "ok"}

@app.get("/history")
async def get_history():
    return history[::-1] if history else [{"temp": 0.0, "hum": 0.0, "time": "—"}]
