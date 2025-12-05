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

# Модель — тільки температура
class Temp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    temp = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "temp": self.temp
        }

# Створюємо базу при старті
with app.app_context():
    db.create_all()

# Головна сторінка — тепер не 404
@app.route('/')
def home():
    return "Temp-stat2 працює – тільки температура! Готовий приймати дані на /data"

# Прийом даних від ESP32
@app.route('/data', methods=['POST'])
def receive_data():
    try:
        data = request.get_json(force=True)
        temp = float(data['temp'])
        
        new_reading = Temp(temp=temp)
        db.session.add(new_reading)
        db.session.commit()
        
        print(f"Отримано температуру: {temp}°C")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"Помилка: {e}")
        return jsonify({"error": str(e)}), 400

# Віддача даних для графіку
@app.route('/api/data')
def api_data():
    limit = request.args.get('limit', 1500, type=int)
    readings = Temp.query.order_by(Temp.timestamp.desc()).limit(limit).all()
    readings.reverse()  # від старого до нового
    return jsonify([r.to_dict() for r in readings])

# Запуск (тільки для локального тесту)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
