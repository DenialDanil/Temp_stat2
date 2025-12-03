from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Зберігаємо історію в пам’яті (вистачить на години/дні)
history = []

@app.post("/data")
async def receive(data: dict):           # ← просто dict, а не окремі параметри
    item = {
        "temp": data.get("temp", 0),
        "hum": data.get("hum", 0),
        "relay": data.get("relay", 0),
        "time": datetime.utcnow().strftime("%H:%M:%S")
    }
    history.append(item)
    if len(history) > 500:
        history.pop(0)
    print("Отримано:", item)
    return {"status": "ok", "total": len(history)}

@app.get("/history")
async def get_history():
    return history[::-1]  # від нових до старих

@app.get("/")
async def root():
    return {"message": "Temp_stat працює! Дані: /history"}
