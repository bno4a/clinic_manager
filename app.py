from datetime import date

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user, login_required)

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///clinic.db"
app.config["SECRET_KEY"] = "clinic-secret-key"

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Войдите, чтобы продолжить."

# Фиксированное расписание приёма: одинаковые слоты для всех врачей на любой день
SLOTS = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]


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


# Flask-Login хранит в сессии только id пользователя. На каждом запросе он вызывает
# эту функцию, чтобы по id получить объект Patient — он и будет current_user
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Patient, int(user_id))


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
    doctors = Doctor.query.order_by(Doctor.name).all()
    return render_template("index.html", doctors=doctors)


# <int:doctor_id> — часть адреса, которая превращается в число и передаётся в функцию.
# Например, /doctor/2 -> doctor_page(doctor_id=2)
@app.route("/doctor/<int:doctor_id>")
def doctor_page(doctor_id):
    # Ищем врача по первичному ключу; если такого нет — страница 404 "Not Found"
    doctor = db.get_or_404(Doctor, doctor_id)

    # request.args — параметры из адреса после "?", например /doctor/2?date=2026-10-01.
    # date.fromisoformat превращает строку "2026-10-01" в объект даты.
    # Если параметра нет или он неправильный — ValueError, тогда берём сегодня.
    try:
        selected_date = date.fromisoformat(request.args.get("date", ""))
    except ValueError:
        selected_date = date.today()

    # Все записи к этому врачу на выбранную дату
    appointments = Appointment.query.filter_by(doctor_id=doctor.id,
                                               date=selected_date).all()
    # Занятое время — список строк вида "10:00"
    booked_times = [a.time for a in appointments]
    # Свободные слоты — те, которых нет среди занятых
    free_slots = [slot for slot in SLOTS if slot not in booked_times]

    # today нужен шаблону, чтобы запретить выбор прошедших дат в календаре
    return render_template("doctor.html", doctor=doctor, today=date.today(),
                           selected_date=selected_date, free_slots=free_slots)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # request.form — данные из полей формы (ключ = атрибут name у <input>)
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]

        if not name or not email or not password:
            flash("Заполните все поля.")
            return redirect(url_for("register"))

        # Проверяем, что такой email ещё не занят
        if Patient.query.filter_by(email=email).first():
            flash("Пользователь с таким email уже зарегистрирован.")
            return redirect(url_for("register"))

        # В БД сохраняем не пароль, а его хеш с солью
        patient = Patient(name=name, email=email,
                          password_hash=generate_password_hash(password))
        db.session.add(patient)
        db.session.commit()

        login_user(patient)  # сразу входим под новым пользователем
        flash("Регистрация прошла успешно!")
        return redirect(url_for("index"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"]

        patient = Patient.query.filter_by(email=email).first()
        if patient and check_password_hash(patient.password_hash, password):
            login_user(patient)  # запоминаем пользователя в сессии
            flash(f"Здравствуйте, {patient.name}!")
            return redirect(url_for("index"))

        flash("Неверный email или пароль.")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
@login_required  # выйти может только тот, кто вошёл
def logout():
    logout_user()  # удаляем пользователя из сессии
    flash("Вы вышли из аккаунта.")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
