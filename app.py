from flask import Flask, request, jsonify
from database import db, Measurement
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Створюємо базу
with app.app_context():
    db.create_all()

@app.route('/data', methods=['POST'])
def receive_data():
    try:
        data = request.get_json(force=True)
        print(f"Отримано: {data}")

        measurement = Measurement(
            soil=int(data['soil']),
            temp=float(data['temp']),
            hum=float(data['hum'])
        )
        db.session.add(measurement)
        db.session.commit()

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"Помилка: {e}")
        return jsonify({"error": str(e)}), 400

@app.route('/api/data')
def api_data():
    limit = request.args.get('limit', 500, type=int)
    measurements = Measurement.query.order_by(Measurement.timestamp.desc()).limit(limit).all()
    measurements.reverse()
    return jsonify([m.to_dict() for m in measurements])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
