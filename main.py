from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os
import csv

app = Flask(__name__)

# Правильний шлях до бази на Render (пише тільки в /data)
db_folder = "/data" if os.path.exists("/data") else "."
db_path = os.path.join(db_folder, "data.db")
os.makedirs(db_folder, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
db = SQLAlchemy(app)

# Модель — усі датчики
class Measurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    temp = db.Column(db.Float, nullable=False)      # температура °C
    co2 = db.Column(db.Integer, nullable=False)     # CO₂ від MQ-135 (ppm)
    tvoc = db.Column(db.Integer, nullable=False)    # TVOC від CCS811 (ppb)
    light = db.Column(db.Integer, nullable=False)   # освітленість (0–4095)

    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "temp": self.temp,
            "co2": self.co2,
            "tvoc": self.tvoc,
            "light": self.light
        }

# Створюємо таблицю
with app.app_context():
    db.create_all()

# Шлях до папки для збереження файлів (в /data на Render)
data_folder = db_folder
csv_path = os.path.join(data_folder, "measurements.csv")

# Створюємо CSV файл, якщо немає (з заголовками)
if not os.path.exists(csv_path):
    with open(csv_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", "temp", "co2", "tvoc", "light"])

# Головна сторінка
@app.route('/')
def home():
    return "Temp-stat2 працює – температура + CO₂ + TVOC + освітленість!"

# Прийом даних від ESP32
@app.route('/data', methods=['POST'])
def receive_data():
    try:
        data = request.get_json(force=True)
        
        temp = float(data.get('temp', 0.0))
        co2 = int(data.get('co2', 0))
        tvoc = int(data.get('tvoc', 0))
        light = int(data.get('light', 0))

        m = Measurement(temp=temp, co2=co2, tvoc=tvoc, light=light)
        db.session.add(m)
        db.session.commit()

        # Додаткове збереження в CSV файл у папку /data (зберігається після перезапуску)
        with open(csv_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([m.timestamp.isoformat(), m.temp, m.co2, m.tvoc, m.light])

        print(f"Отримано: T={temp}°C | CO₂={co2}ppm | TVOC={tvoc}ppb | Light={light}")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"Помилка: {e}")
        return jsonify({"error": str(e)}), 400

# API для графіку
@app.route('/api/data')
def api_data():
    limit = request.args.get('limit', 3000, type=int)
    readings = Measurement.query.order_by(Measurement.timestamp.desc()).limit(limit).all()
    readings.reverse()  # від старого до нового
    return jsonify([r.to_dict() for r in readings])

# Запуск
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
