from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os

app = Flask(__name__)

# Шлях до бази на Render
db_folder = "/data" if os.path.exists("/data") else "."
db_path = os.path.join(db_folder, "data.db")
os.makedirs(db_folder, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
db = SQLAlchemy(app)

class Measurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    temp = db.Column(db.Float, nullable=False)      # від DHT11
    co2 = db.Column(db.Integer, nullable=False)     # від MQ-135 (ppm)
    tvoc = db.Column(db.Integer, nullable=False)    # від CCS811 (ppb)

    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "temp": self.temp,
            "co2": self.co2,
            "tvoc": self.tvoc
        }

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return "Temp-stat2 працює – T + CO₂ (MQ-135) + TVOC (CCS811)"

@app.route('/data', methods=['POST'])
def receive_data():
    try:
        data = request.get_json(force=True)
        temp = float(data.get('temp', 0.0))
        co2 = int(data.get('co2', 0))
        tvoc = int(data.get('tvoc', 0))

        m = Measurement(temp=temp, co2=co2, tvoc=tvoc)
        db.session.add(m)
        db.session.commit()

        print(f"Отримано: T={temp}°C, CO₂={co2}ppm, TVOC={tvoc}ppb")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"Помилка: {e}")
        return jsonify({"error": str(e)}), 400

@app.route('/api/data')
def api_data():
    limit = request.args.get('limit', 2000, type=int)
    readings = Measurement.query.order_by(Measurement.timestamp.desc()).limit(limit).all()
    readings.reverse()
    return jsonify([r.to_dict() for r in readings])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
