class Measurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    temp = db.Column(db.Float, nullable=False)
    co2 = db.Column(db.Integer, nullable=False)
    tvoc = db.Column(db.Integer, nullable=False)
    light = db.Column(db.Integer, nullable=False, default=0)  # ← освітленість

    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "temp": self.temp,
            "co2": self.co2,
            "tvoc": self.tvoc,
            "light": self.light
        }

@app.route('/data', methods=['POST'])
def receive_data():
    try:
        data = request.get_json(force=True)
        temp = float(data.get('temp', 0))
        co2 = int(data.get('co2', 0))
        tvoc = int(data.get('tvoc', 0))
        light = int(data.get('light', 0))

        m = Measurement(temp=temp, co2=co2, tvoc=tvoc, light=light)
        db.session.add(m)
        db.session.commit()

        print(f"T={temp}°C | CO₂={co2}ppm | TVOC={tvoc}ppb | Light={light}")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"Помилка: {e}")
        return jsonify({"error": str(e)}), 400
