from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import os
from zoneinfo import ZoneInfo  # НОВЕ: для часових зон (Python 3.9+)

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app, resources={r"/*": {"origins": "*"}})
db = SQLAlchemy(app)

class Measurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # Зберігаємо в UTC
    temp = db.Column(db.Float, nullable=False)
    co2 = db.Column(db.Integer, nullable=False)
    tvoc = db.Column(db.Integer, nullable=False)
    light = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        # НОВЕ: Конвертуємо timestamp з UTC в Київський час
        kyiv_tz = ZoneInfo("Europe/Kyiv")
        local_timestamp = self.timestamp.replace(tzinfo=ZoneInfo("UTC")).astimezone(kyiv_tz)
        
        return {
            "timestamp": local_timestamp.isoformat(),  # Тепер з київським часом і +02:00/+03:00
            "temp": self.temp,
            "co2": self.co2,
            "tvoc": self.tvoc,
            "light": self.light
        }

with app.app_context():
    db.create_all()

# Очищення — залишаємо на UTC (щоб правильно працювало)
def cleanup_old_data():
    cutoff = datetime.utcnow() - timedelta(days=2)
    deleted = Measurement.query.filter(Measurement.timestamp < cutoff).delete()
    db.session.commit()
    if deleted > 0:
        print(f"Видалено {deleted} старих записів")

@app.route('/')
def home():
    cleanup_old_data()
    return "<h1>Temp-m2 на Railway</h1><p>Backend з PostgreSQL працює! Час — київський.</p>"

@app.route('/data', methods=['POST'])
def receive_data():
    cleanup_old_data()
    try:
        data = request.get_json(force=True)
        m = Measurement(
            temp=float(data.get('temp', 0.0)),
            co2=int(data.get('co2', 0)),
            tvoc=int(data.get('tvoc', 0)),
            light=int(data.get('light', 0))
        )
        db.session.add(m)
        db.session.commit()
        print(f"Отримано: T={m.temp}°C | CO₂={m.co2}ppm | TVOC={m.tvoc}ppb | Light={m.light}")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Помилка: {e}")
        return jsonify({"error": str(e)}), 400

# API — всі повертають час вже в київській зоні
@app.route('/api/data')
def api_data():
    cleanup_old_data()
    two_days_ago = datetime.utcnow() - timedelta(days=2)
    readings = Measurement.query.filter(Measurement.timestamp >= two_days_ago)\
                               .order_by(Measurement.timestamp.asc()).all()
    return jsonify([r.to_dict() for r in readings])

@app.route('/api/today')
def api_today():
    today_start_utc = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    readings = Measurement.query.filter(Measurement.timestamp >= today_start_utc)\
                               .order_by(Measurement.timestamp.asc()).all()
    return jsonify([r.to_dict() for r in readings])

@app.route('/api/yesterday')
def api_yesterday():
    yesterday_start_utc = (datetime.utcnow() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_end_utc = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    readings = Measurement.query.filter(Measurement.timestamp >= yesterday_start_utc, Measurement.timestamp < yesterday_end_utc)\
                               .order_by(Measurement.timestamp.asc()).all()
    return jsonify([r.to_dict() for r in readings])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
