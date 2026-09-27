from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///clinic.db"

db = SQLAlchemy(app)


# ---------- МОДЕЛИ (таблицы БД) ----------
class Patient(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    appointments = db.relationship("Appointment", backref="patient")


class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    specialty = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    appointments = db.relationship("Appointment", backref="doctor")


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(5), nullable=False)


# ---------- СОЗДАНИЕ БД И НАЧАЛЬНЫЕ ДАННЫЕ ----------
with app.app_context():
    db.create_all()

    # Если врачей нет — добавляем нескольких
    if Doctor.query.count() == 0:
        db.session.add_all([
            Doctor(name="Иванова Анна Петровна", specialty="Терапевт",
                   description="Приём взрослых пациентов, общие заболевания."),
            Doctor(name="Смирнов Олег Игоревич", specialty="Кардиолог",
                   description="Болезни сердца и сосудов, ЭКГ."),
            Doctor(name="Кузнецова Мария Сергеевна", specialty="Невролог",
                   description="Головные боли, болезни нервной системы."),
            Doctor(name="Попов Дмитрий Андреевич", specialty="Стоматолог",
                   description="Лечение и профилактика заболеваний зубов."),
        ])
        db.session.commit()


# ---------- МАРШРУТЫ ----------
@app.route("/")
def index():
    doctors = Doctor.query.all()
    return "<br>".join(f"{d.name} — {d.specialty}" for d in doctors)


if __name__ == "__main__":
    app.run(debug=True)
