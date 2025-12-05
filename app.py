from flask import Flask, request, jsonify
from database import db, Measurement
from flask_cors import CORS
import os

app = Flask(__name__)

# На Render використовуємо /data — єдиний записуваний шлях
db_folder = "/data" if os.path.exists("/data") else "instance"
db_path = os.path.join(db_folder, "data.db")
os.makedirs(db_folder, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)  # Дозволяємо запити з Temp-m2.onrender.com
db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return "Temp-stat2 бекенд працює!"

@app.route('/data', methods=['POST'])
def receive_data():
    try:
        data = request.get_json(force=True)
        print(f"Отримано: {data}")

        m = Measurement(
            soil=int(data['soil']),
            temp=float(data['temp']),
            hum=float(data['hum'])
        )
        db.session.add(m)
        db.session.commit()
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"Помилка: {e}")
        return jsonify({"error": str(e)}), 400

@app.route('/api/data')
def api_data():
    limit = request.args.get('limit', 1500, type=int)
    measurements = Measurement.query.order_by(Measurement.timestamp.desc()).limit(limit).all()
    measurements.reverse()
    return jsonify([m.to_dict() for m in measurements])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
