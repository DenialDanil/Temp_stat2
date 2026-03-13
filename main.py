from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import requests
from zoneinfo import ZoneInfo

app = Flask(__name__)

# --- Налаштування бази даних ---
# Railway автоматично надає DATABASE_URL
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app, resources={r"/*": {"origins": "*"}})
db = SQLAlchemy(app)

# --- Налаштування Telegram ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# Словник для збереження часу останнього сповіщення (щоб не було спаму)
# Зберігається в оперативній пам'яті сервера
last_alerts = {
    "co2": None,
    "tvoc": None,
    "temp": None,
    "light": None
}

# Інтервал між повторними сповіщеннями (наприклад, 10 хвилин)
ALERT_INTERVAL = timedelta(seconds=10)

# --- Модель бази даних ---
class Measurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    temp = db.Column(db.Float, nullable=False)
    co2 = db.Column(db.Integer, nullable=False)
    tvoc = db.Column(db.Integer, nullable=False)
    light = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        kyiv_tz = ZoneInfo("Europe/Kyiv")
        local_timestamp = self.timestamp.replace(tzinfo=ZoneInfo("UTC")).astimezone(kyiv_tz)
        return {
            "timestamp": local_timestamp.isoformat(),
            "temp": self.temp,
            "co2": self.co2,
            "tvoc": self.tvoc,
            "light": self.light
        }

# Створення таблиць
with app.app_context():
    db.create_all()

# --- Допоміжні функції ---

def send_telegram_alert(text):
    """Відправка повідомлення в Telegram за допомогою API"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Помилка: Telegram змінні не налаштовані!")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Помилка відправки в Telegram: {e}")

def check_and_notify(temp, co2, tvoc, light):
    """Логіка перевірки порогів та анти-спаму"""
    global last_alerts
    now = datetime.utcnow()
    
    # 1. Перевірка CO2
    if co2 > 1200:
        if last_alerts["co2"] is None or (now - last_alerts["co2"]) > ALERT_INTERVAL:
            send_telegram_alert(f"⚠️ *Високий рівень CO₂!* \nЗначення: `{co2} ppm`. \nБудь ласка, відкрийте вікно!")
            last_alerts["co2"] = now

    # 2. Перевірка TVOC
    if tvoc > 660:
        if last_alerts["tvoc"] is None or (now - last_alerts["tvoc"]) > ALERT_INTERVAL:
            send_telegram_alert(f"☣️ *Повітря забруднене (TVOC)!* \nЗначення: `{tvoc} ppb`. \nРекомендується провітрювання.")
            last_alerts["tvoc"] = now

    # 3. Перевірка Температури
    if temp > 28:
        if last_alerts["temp"] is None or (now - last_alerts["temp"]) > ALERT_INTERVAL:
            send_telegram_alert(f"🔥 *Занадто спекотно!* \nТемпература: `{temp}°C`.")
            last_alerts["temp"] = now
    elif temp < 18:
        if last_alerts["temp"] is None or (now - last_alerts["temp"]) > ALERT_INTERVAL:
            send_telegram_alert(f"❄️ *Занадто холодно!* \nТемпература: `{temp}°C`.")
            last_alerts["temp"] = now

    # 4. Перевірка Освітленості//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    #if light < 100:
       # if last_alerts["light"] is None or (now - last_alerts["light"]) > ALERT_INTERVAL:
            #send_telegram_alert(f"🌑 *Недостатньо світла!* \nРівень: `{light} lux`. Це може втомлювати очі.")
           # last_alerts["light"] = now

def cleanup_old_data():
    """Видалення даних старше 2 днів"""
    cutoff = datetime.utcnow() - timedelta(days=2)
    try:
        deleted = Measurement.query.filter(Measurement.timestamp < cutoff).delete()
        db.session.commit()
        if deleted > 0:
            print(f"Очищено записів: {deleted}")
    except Exception as e:
        db.session.rollback()
        print(f"Помилка очищення: {e}")

def get_today_start_kyiv():
    """Повертає 00:00 сьогодні за Києвом в UTC"""
    kyiv_tz = ZoneInfo("Europe/Kyiv")
    now_kyiv = datetime.now(kyiv_tz)
    today_start_kyiv = now_kyiv.replace(hour=0, minute=0, second=0, microsecond=0)
    return today_start_kyiv.astimezone(ZoneInfo("UTC"))

# --- Маршрути (Routes) ---

@app.route('/')
def home():
    cleanup_old_data()
    return "<h1>Система моніторингу довкілля</h1><p>Статус: Працює</p>"

@app.route('/data', methods=['POST'])
def receive_data():
    """Прийом даних від ESP32"""
    cleanup_old_data()
    try:
        data = request.get_json(force=True)
        
        # Витягуємо значення
        t = float(data.get('temp', 0.0))
        c = int(data.get('co2', 0))
        v = int(data.get('tvoc', 0))
        l = int(data.get('light', 0))

        # Зберігаємо в базу
        m = Measurement(temp=t, co2=c, tvoc=v, light=l)
        db.session.add(m)
        db.session.commit()

        # Перевіряємо пороги для Telegram
        check_and_notify(t, c, v, l)

        print(f"Дані отримано: CO2={c}, T={t}")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Помилка POST: {e}")
        return jsonify({"error": str(e)}), 400

@app.route('/api/data')
def api_data():
    """Отримати всі дані за останні 2 дні"""
    two_days_ago = datetime.utcnow() - timedelta(days=2)
    readings = Measurement.query.filter(Measurement.timestamp >= two_days_ago)\
                          .order_by(Measurement.timestamp.asc()).all()
    return jsonify([r.to_dict() for r in readings])

@app.route('/api/today')
def api_today():
    """Дані за сьогодні (від 00:00 за Києвом)"""
    today_start_utc = get_today_start_kyiv()
    readings = Measurement.query.filter(Measurement.timestamp >= today_start_utc)\
                          .order_by(Measurement.timestamp.asc()).all()
    return jsonify([r.to_dict() for r in readings])

@app.route('/api/yesterday')
def api_yesterday():
    """Дані за вчора"""
    today_start_utc = get_today_start_kyiv()
    yesterday_start_utc = today_start_utc - timedelta(days=1)
    readings = Measurement.query.filter(
        Measurement.timestamp >= yesterday_start_utc,
        Measurement.timestamp < today_start_utc
    ).order_by(Measurement.timestamp.asc()).all()
    return jsonify([r.to_dict() for r in readings])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
