from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

history = []  # сюди пишуться всі дані

@app.post("/data")
async def receive(temp: float, hum: float, relay: int = 0):
    item = {"temp": temp, "hum": hum, "relay": relay, "time": datetime.utcnow().strftime("%H:%M:%S")}
    history.append(item)
    if len(history) > 500:
        history.pop(0)
    print("Отримано:", item)
    return {"status": "ok"}

@app.get("/data")
async def last():
    return history[-1] if history else {"temp":0,"hum":0,"time":"—"}

@app.get("/history")                 # ← ЦЕЙ РЯДОК ДОДАЄШ
async def get_history():
    return history[::-1]             # ← І ЦЕЙ
