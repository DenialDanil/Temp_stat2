from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta, date
import os
import csv
import shutil

app = Flask(__name__)

# Шлях до /data на Render
db_folder = "/data" if os.path.exists("/data") else "."
os.makedirs(db_folder, exist_ok=True)

# Налаштування БД
db_path = os.path.join(db_folder, "data.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
db = SQLAlchemy(app)

# Модель
class Measurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    temp = db.Column(db.Float, nullable=False)
    co2 = db.Column(db.Integer, nullable=False)
    tvoc = db.Column(db.Integer, nullable=False)
    light = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "temp": self.temp,
            "co2": self.co2,
            "tvoc": self.tvoc,
            "light": self.light
        }

with app.app_context():
    db.create_all()

# Шляхи до файлів
today_csv = os.path.join(db_folder, "today.csv")
yesterday_csv = os.path.join(db_folder, "yesterday.csv")

# --- Ініціалізація CSV файлів (якщо їх немає) ---
def init_csv_files():
    today = date.today()
    header = ["timestamp", "temp", "co2", "tvoc", "light"]

    if not os.path.exists(today_csv):
        with open(today_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)

    if not os.path.exists(yesterday_csv):
        with open(yesterday_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)

init_csv_files()

# --- Перевірка і ротація файлів при новій добі ---
def rotate_daily_files_if_needed():
    today = date.today()
    today_str = today.isoformat()

    # Перевіряємо, чи перший рядок у today.csv має сьогоднішню дату
    if os.path.exists(today_csv) and os.path.getsize(today_csv) > 0:
        with open(today_csv, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line.startswith('#') or ',' not in first_line:
                return  # це заголовок — все ок

            try:
                first_timestamp = first_line.split(',')[0]
                first_date = datetime.fromisoformat(first_timestamp.replace('Z', '+00:00')).date()
                if first_date == today:
                    return  # вже правильний файл
            except:
                pass

    print(f"Нова доба! Ротація файлів: {today}")

    # 1. Старий yesterday.csv → видаляємо
    if os.path.exists(yesterday_csv):
        os.remove(yesterday_csv)
        print("Видалено старий yesterday.csv")

    # 2. today.csv → перейменовуємо в yesterday.csv
    if os.path.exists(today_csv):
        shutil.move(today_csv, yesterday_csv)
        print("today.csv → yesterday.csv")

    # 3. Створюємо новий today.csv
    with open(today_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "temp", "co2", "tvoc", "light"])
    print("Створено новий today.csv")

    # 4. Очищаємо БД — залишаємо тільки сьогодні + вчора
    cutoff = datetime.combine(today - timedelta(days=1), datetime.min.time())
    deleted = Measurement.query.filter(Measurement.timestamp < cutoff).delete()
    db.session.commit()
    if deleted:
        print(f"Видалено {deleted} записів старше вчорашнього дня з БД")

# Головна
@app.route('/')
def home():
    rotate_daily_files_if_needed()
    return "Temp-stat2: дані за сьогодні та вчора зберігаються окремо!"

# Прийом даних
@app.route('/data', methods=['POST'])
def receive_data():
    rotate_daily_files_if_needed()  # важливо: перевіряємо кожен раз

    try:
        data = request.get_json(force=True)
        temp = float(data.get('temp', 0.0))
        co2 = int(data.get('co2', 0))
        tvoc = int(data.get('tvoc', 0))
        light = int(data.get('light', 0))

        m = Measurement(temp=temp, co2=co2, tvoc=tvoc, light=light)
        db.session.add(m)
        db.session.commit()

        # Записуємо в today.csv
        with open(today_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([m.timestamp.isoformat(), m.temp, m.co2, m.tvoc, m.light])

        print(f"Записано: {temp}°C, CO₂={co2}, TVOC={tvoc}, Light={light}")

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Помилка: {e}")
        return jsonify({"error": str(e)}), 400

# API: всі дані за сьогодні + вчора
@app.route('/api/data')
def api_data():
    rotate_daily_files_if_needed()

    two_days_ago = datetime.utcnow() - timedelta(days=2)
    readings = Measurement.query.filter(Measurement.timestamp >= two_days_ago)\
                               .order_by(Measurement.timestamp.asc())\
                               .all()

    return jsonify([r.to_dict() for r in readings])

# Додаткові ендпоінти (корисно для фронтенду або дебагу)
@app.route('/api/today')
def api_today():
    with open(today_csv, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    data = []
    for line in lines[1:]:  # пропускаємо заголовок
        if line.strip():
            parts = line.strip().split(',')
            data.append({
                "timestamp": parts[0],
                "temp": float(parts[1]),
                "co2": int(parts[2]),
                "tvoc": int(parts[3]),
                "light": int(parts[4])
            })
    return jsonify(data)

@app.route('/api/yesterday')
def api_yesterday():
    if not os.path.exists(yesterday_csv):
        return jsonify([])
    with open(yesterday_csv, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    data = []
    for line in lines[1:]:
        if line.strip():
            parts = line.strip().split(',')
            data.append({
                "timestamp": parts[0],
                "temp": float(parts[1]),
                "co2": int(parts[2]),
                "tvoc": int(parts[3]),
                "light": int(parts[4])
            })
    return jsonify(data)

# Примусова ротація (для тестів)
@app.route('/rotate')
def force_rotate():
    rotate_daily_files_if_needed()
    return jsonify({"status": "rotated"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
