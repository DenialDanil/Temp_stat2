from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

dani = []

@app.post("/data")
async def receive(temp: float, hum: float):
    item = {"temp": temp, "hum": hum, "time": datetime.now().strftime("%H:%M:%S")}
    dani.append(item)
    if len(dani) > 500:
        dani.pop(0)
    print("Отримано:", item)
    return {"status": "}

@app.get("/data")
async def last():
    return dani[-1] if dani else {"temp": 0, "hum": 0, "time": "--:--"}

@app.get("/history")
async def history():
    return dani[::-1]
