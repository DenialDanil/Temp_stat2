from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Measurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    soil = db.Column(db.Integer, nullable=False)      # 0-4095
    temp = db.Column(db.Float, nullable=False)        # °C
    hum = db.Column(db.Float, nullable=False)         # %

    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "soil": self.soil,
            "temp": self.temp,
            "hum": self.hum
        }
