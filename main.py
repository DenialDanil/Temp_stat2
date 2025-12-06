from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os

app = Flask(__name__)

# Правильний шлях до бази на Render (запис тільки в /data)
db_folder = "/data" if os.path.exists("/data") else "."
db_path = os.path.join(db_folder, "data.db")
os.makedirs(db_folder, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)  # дозволяє запити з temp-m2.onrender.com
db = SQLAlchemy(app)

# Модель — температура + CO2
class Measurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    temp = db.Column(db.Float, nullable=False)
    co2 = db.Column(db.Integer, nullable=False, default=0)  # додали CO2 в ppm

    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "temp": self.temp,
            "co2": self.co2
        }

# Створюємо базу при старті
with app.app_context():
    db.create_all()

# Головна сторінка — тепер не 404
@app.route('/')
def home():
    return "Temp-stat2 працює – температура + CO2! Готовий приймати дані на /data"

# Прийом даних від ESP32 (температура + CO2)
@app.route('/data', methods=['POST'])
def receive_data():
    try:
        data = request.get_json(force=True)
        temp = float(data.get('temp', 0.0))
        co2 = int(data.get('co2', 0))
        
        new_reading = Measurement(temp=temp, co2=co2)
        db.session.add(new_reading)
        db.session.commit()
        
        print(f"Отримано: T={temp}°C, CO2={co2}ppm")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"Помилка: {e}")
        return jsonify({"error": str(e)}), 400

# Віддача даних для графіку (температура + CO2)
@app.route('/api/data')
def api_data():
    limit = request.args.get('limit', 1500, type=int)
    readings = Measurement.query.order_by(Measurement.timestamp.desc()).limit(limit).all()
    readings.reverse()  # від старого до нового
    return jsonify([r.to_dict() for r in readings])

# Запуск (тільки для локального тесту)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
