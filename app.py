from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os

app = Flask(__name__)

# На Render база лежить у /data
db_path = "/data/data.db" if os.path.exists("/data") else "instance/data.db"
os.makedirs(os.path.dirname(db_path), exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
db = SQLAlchemy(app)

class Temp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    temp = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {"timestamp": self.timestamp.isoformat(), "temp": self.temp}

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return "Temp-stat2 працює – тільки температура!"

@app.route('/data', methods=['POST'])
def receive_data():
    try:
        data = request.get_json(force=True)
        temp = float(data['temp'])
        
        t = Temp(temp=temp)
        db.session.add(t)
        db.session.commit()
        print(f"Отримано температуру: {temp}°C")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/data')
def api_data():
    limit = request.args.get('limit', 1500, type=int)
    readings = Temp.query.order_by(Temp.timestamp.desc()).limit(limit).all()
    readings.reverse()
    return jsonify([r.to_dict() for r in readings])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
