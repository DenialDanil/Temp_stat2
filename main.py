from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import os
from zoneinfo import ZoneInfo

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app, resources={r"/*": {"origins": "*"}})
db = SQLAlchemy(app)

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

with app.app_context():
    db.create_all()

def cleanup_old_data():
    cutoff = datetime.utcnow() - timedelta(days=2)
    deleted = Measurement.query.filter(Measurement.timestamp < cutoff).delete()
    db.session.commit()
    if deleted > 0:
        print(f"Видалено {deleted} старих записів")

# === Симуляція: поділ по 22:41 за Києвом ===
def get_split_point_kyiv():
    """Повертає поточний момент 22:41 за Києвом (сьогодні), в UTC"""
    kyiv_tz = ZoneInfo("Europe/Kyiv")
    now_kyiv = datetime.now(kyiv_tz)
    split_today_kyiv = now_kyiv.replace(hour=22, minute=41, second=0, microsecond=0)
    return split_today_kyiv.astimezone(ZoneInfo("UTC"))

@app.route('/')
def home():
    cleanup_old_data()
    return "<h1>Temp-m2 симуляція</h1><p>Поділ 'сьогодні/вчора' по 22:41 за Києвом</p>"

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

@app.route('/api/data')
def api_data():
    cleanup_old_data()
    two_days_ago = datetime.utcnow() - timedelta(days=2)
    readings = Measurement.query.filter(Measurement.timestamp >= two_days_ago)\
                               .order_by(Measurement.timestamp.asc()).all()
    return jsonify([r.to_dict() for r in readings])

@app.route('/api/today')
def api_today():
    split_point_utc = get_split_point_kyiv()
    readings = Measurement.query.filter(Measurement.timestamp >= split_point_utc)\
                               .order_by(Measurement.timestamp.asc()).all()
    return jsonify([r.to_dict() for r in readings])

@app.route('/api/yesterday')
def api_yesterday():
    split_point_today_utc = get_split_point_kyiv()
    split_point_yesterday_utc = split_point_today_utc - timedelta(days=1)
    readings = Measurement.query.filter(
        Measurement.timestamp >= split_point_yesterday_utc,
        Measurement.timestamp < split_point_today_utc
    ).order_by(Measurement.timestamp.asc()).all()
    return jsonify([r.to_dict() for r in readings])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
