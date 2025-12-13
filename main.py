# app.py — ОСТАТОЧНА ВЕРСІЯ (Render, Railway, Fly.io тощо)

from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta, date
import os
import csv
import shutil

app = Flask(__name__)

# === ПАПКА ДЛЯ ДАНИХ НА RENDER ===
db_folder = "/data" if os.path.exists("/data") else "."
os.makedirs(db_folder, exist_ok=True)

# === БАЗА ДАНИХ ===
db_path = os.path.join(db_folder, "data.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# === CORS — дозволяє запити з будь-якого фронтенду ===
CORS(app, resources={r"/*": {"origins": "*"}})

db = SQLAlchemy(app)

# === МОДЕЛЬ ===
class Measurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    temp = db.Column(db.Float, nullable=False)
    co2 = db.Column(db.Integer, nullable=False)
    tvoc = db.Column(db.Integer, nullable=False)
    light = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "temp": self.temp,
            "co2": self.co2,
            "tvoc": self.tvoc,
            "light": self.light
        }

with app.app_context():
    db.create_all()

# === ШЛЯХИ ДО CSV ===
today_csv = os.path.join(db_folder, "today.csv")
yesterday_csv = os.path.join(db_folder, "yesterday.csv")

# === ІНІЦІАЛІЗАЦІЯ ФАЙЛІВ ===
def init_csv():
    header = ["timestamp", "temp", "co2", "tvoc", "light"]
    for path in (today_csv, yesterday_csv):
        if not os.path.exists(path):
            with open(path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(header)

init_csv()

# === РОТАЦІЯ ФАЙЛІВ ПРИ НОВІЙ ДОБІ ===
def rotate_if_new_day():
    today = date.today()
    if not os.path.exists(today_csv) or os.path.getsize(today_csv) == 0:
        return  # ще немає даних

    # Перевіряємо дату першого рядка у today.csv
    with open(today_csv, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
        if not first_line or first_line.startswith("timestamp"):
            return
        try:
            first_ts = datetime.fromisoformat(first_line.split(",")[0].replace("Z", "+00:00"))
            if first_ts.date() == today:
                return
        except:
            pass

    print(f"Нова доба ({today}) — ротація файлів...")

    # 1. Видаляємо старий yesterday.csv
    if os.path.exists(yesterday_csv):
        os.remove(yesterday_csv)

    # 2. today.csv → yesterday.csv
    if os.path.exists(today_csv):
        shutil.move(today_csv, yesterday_csv)

    # 3. Новий today.csv
    with open(today_csv, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["timestamp", "temp", "co2", "tvoc", "light"])

    # 4. Очищаємо БДД — залишаємо тільки сьогодні + вчора
    cutoff = datetime.combine(today - timedelta(days=1), datetime.min.time())
    deleted = Measurement.query.filter(Measurement.timestamp < cutoff).delete()
    db.session.commit()
    if deleted:
        print(f"Видалено {deleted} старих записів з БД")

# === ГОЛОВНА ===
@app.route('/')
def home():
    rotate_if_new_day()
    return "<h1>Temp-m2 працює</h1><p>Дані за сьогодні + вчора. Все ок!</p>"

# === ПРИЙОМ ДАНИХ ВІД ESP32 ===
@app.route('/data', methods=['POST'])
def receive_data():
    rotate_if_new_day()
    try:
        data = request.get_json(force=True)
        m = Measurement(
            temp=float(data.get('temp', 0)),
            co2=int(data.get('co2', 0)),
            tvoc=int(data.get('tvoc', 0)),
            light=int(data.get('light', 0))
        )
        db.session.add(m)
        db.session.commit()

        # Запис у today.csv
        with open(today_csv, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([m.timestamp.isoformat(), m.temp, m.co2, m.tvoc, m.light])

        print(f"Отримано: {m.temp}°C | CO₂ {m.co2} | TVOC {m.tvoc} | Light {m.light}")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

# === API ===
@app.route('/api/data')
def api_all():
    rotate_if_new_day()
    two_days_ago = datetime.utcnow() - timedelta(days=2)
    readings = Measurement.query.filter(Measurement.timestamp >= two_days_ago)\
                               .order_by(Measurement.timestamp.asc()).all()
    return jsonify([r.to_dict() for r in readings])

@app.route('/api/today')
def api_today():
    rotate_if_new_day()
    if not os.path.exists(today_csv):
        return jsonify([])
    with open(today_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        data = [row for row in reader]
    return jsonify([{**row, "temp": float(row["temp"])} for row in data])

@app.route('/api/yesterday')
def api_yesterday():
    if not os.path.exists(yesterday_csv):
        return jsonify([])
    with open(yesterday_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        data = [row for row in reader]
    return jsonify([{**row, "temp": float(row["temp"])} for row in data])

# === СКАЧУВАННЯ ФАЙЛІВ (за бажанням — можеш видалити) ===
@app.route('/download/today')
def download_today():    return send_file(today_csv, as_attachment=True)

@app.route('/download/yesterday')
def download_yesterday():return send_file(yesterday_csv, as_attachment=True)

@app.route('/download/db')
def download_db():       return send_file(db_path, as_attachment=True)

# === ЗАПУСК ===
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
