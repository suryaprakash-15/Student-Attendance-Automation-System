import os
import sqlite3
from datetime import date, datetime
from functools import wraps
from pathlib import Path

from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "attendance.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "local-development-secret-change-me")
app.config["DATABASE"] = str(DATABASE_PATH)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    DATABASE_DIR.mkdir(exist_ok=True)
    db = sqlite3.connect(app.config["DATABASE"])
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Teacher',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            roll_number TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            department TEXT NOT NULL,
            year TEXT NOT NULL,
            section TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Present', 'Absent')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            UNIQUE(student_id, attendance_date)
        );
        """
    )
    user = db.execute("SELECT id FROM users WHERE username = ?", ("admin",)).fetchone()
    if not user:
        db.execute(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
            ("admin", generate_password_hash("admin123"), "Administrator", "Teacher"),
        )
    count = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    if count == 0:
        demo_students = [
            ("STU001", "Aarav Sharma", "CSE001", "aarav@example.com", "9876543210", "CSE", "3", "A"),
            ("STU002", "Diya Reddy", "CSE002", "diya@example.com", "9876543211", "CSE", "3", "A"),
            ("STU003", "Kabir Kumar", "CSE003", "kabir@example.com", "9876543212", "CSE", "3", "A"),
            ("STU004", "Meera Patel", "ECE001", "meera@example.com", "9876543213", "ECE", "2", "B"),
            ("STU005", "Rohan Das", "ECE002", "rohan@example.com", "9876543214", "ECE", "2", "B"),
        ]
        db.executemany(
            """INSERT INTO students
            (student_id, name, roll_number, email, phone, department, year, section)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            demo_students,
        )
    db.commit()
    db.close()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def valid_student_form(form):
    fields = ["student_id", "name", "roll_number", "email", "phone", "department", "year", "section"]
    data = {field: form.get(field, "").strip() for field in fields}
    if not all(data.values()):
        return data, "All student fields are required."
    if "@" not in data["email"] or "." not in data["email"].split("@")[-1]:
        return data, "Enter a valid email address."
    if not data["phone"].isdigit() or len(data["phone"]) < 10:
        return data, "Phone number must contain at least 10 digits."
    return data, None


def attendance_summary(student_id=None):
    db = get_db()
    query = "SELECT COUNT(*) AS total, SUM(status = 'Present') AS present FROM attendance"
    params = []
    if student_id:
        query += " WHERE student_id = ?"
        params.append(student_id)
    row = db.execute(query, params).fetchone()
    total = row["total"] or 0
    present = row["present"] or 0
    return total, present, total - present, round((present / total) * 100, 1) if total else 0


@app.route("/")
def home():
    return redirect(url_for("dashboard" if "user_id" in session else "login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.", "danger")
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    today = date.today().isoformat()
    total_students = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    present_today = db.execute("SELECT COUNT(*) FROM attendance WHERE attendance_date = ? AND status = 'Present'", (today,)).fetchone()[0]
    absent_today = db.execute("SELECT COUNT(*) FROM attendance WHERE attendance_date = ? AND status = 'Absent'", (today,)).fetchone()[0]
    total, present, _, percentage = attendance_summary()
    recent = db.execute("""SELECT a.*, s.name, s.roll_number FROM attendance a
        JOIN students s ON s.id = a.student_id ORDER BY a.attendance_date DESC, a.created_at DESC LIMIT 8""").fetchall()
    low_attendance = db.execute("""SELECT s.*, COUNT(a.id) AS total_days,
        COALESCE(SUM(a.status = 'Present'), 0) AS present_days
        FROM students s LEFT JOIN attendance a ON s.id = a.student_id
        GROUP BY s.id HAVING total_days > 0 AND (present_days * 100.0 / total_days) < 75
        ORDER BY (present_days * 1.0 / total_days) ASC""").fetchall()
    return render_template("dashboard.html", total_students=total_students, present_today=present_today,
                           absent_today=absent_today, percentage=percentage, recent=recent,
                           low_attendance=low_attendance, working_days=total, present_days=present)


@app.route("/students")
@login_required
def students():
    db = get_db()
    search = request.args.get("search", "").strip()
    department = request.args.get("department", "").strip()
    section = request.args.get("section", "").strip()
    query = "SELECT * FROM students WHERE (name LIKE ? OR student_id LIKE ? OR roll_number LIKE ?)"
    params = [f"%{search}%"] * 3
    if department:
        query += " AND department = ?"
        params.append(department)
    if section:
        query += " AND section = ?"
        params.append(section)
    query += " ORDER BY name"
    student_rows = db.execute(query, params).fetchall()
    departments = db.execute("SELECT DISTINCT department FROM students ORDER BY department").fetchall()
    sections = db.execute("SELECT DISTINCT section FROM students ORDER BY section").fetchall()
    return render_template("students.html", students=student_rows, departments=departments, sections=sections,
                           search=search, selected_department=department, selected_section=section)


@app.route("/students/add", methods=["GET", "POST"])
@login_required
def add_student():
    data = {}
    if request.method == "POST":
        data, error = valid_student_form(request.form)
        if error:
            flash(error, "danger")
        else:
            try:
                db = get_db()
                db.execute("""INSERT INTO students
                    (student_id, name, roll_number, email, phone, department, year, section)
                    VALUES (:student_id, :name, :roll_number, :email, :phone, :department, :year, :section)""", data)
                db.commit()
                flash("Student added successfully.", "success")
                return redirect(url_for("students"))
            except sqlite3.IntegrityError:
                flash("Student ID or roll number already exists.", "danger")
    return render_template("add_student.html", student=data)


@app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
def edit_student(student_id):
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("students"))
    data = dict(student)
    if request.method == "POST":
        data, error = valid_student_form(request.form)
        if error:
            flash(error, "danger")
        else:
            try:
                db.execute("""UPDATE students SET student_id=:student_id, name=:name, roll_number=:roll_number,
                    email=:email, phone=:phone, department=:department, year=:year, section=:section WHERE id=:id""",
                           {**data, "id": student_id})
                db.commit()
                flash("Student updated successfully.", "success")
                return redirect(url_for("students"))
            except sqlite3.IntegrityError:
                flash("Student ID or roll number already exists.", "danger")
    return render_template("edit_student.html", student=data)


@app.post("/students/<int:student_id>/delete")
@login_required
def delete_student(student_id):
    db = get_db()
    db.execute("DELETE FROM students WHERE id = ?", (student_id,))
    db.commit()
    flash("Student deleted.", "success")
    return redirect(url_for("students"))


@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():
    db = get_db()
    selected_date = request.values.get("attendance_date", date.today().isoformat())
    selected_section = request.values.get("section", "")
    if request.method == "POST":
        try:
            parsed_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
        except ValueError:
            flash("Enter a valid attendance date.", "danger")
        else:
            if parsed_date > date.today():
                flash("Attendance cannot be marked for a future date.", "danger")
            else:
                students_for_save = db.execute("SELECT id FROM students" + (" WHERE section = ?" if selected_section else ""), ([selected_section] if selected_section else [])).fetchall()
                for student in students_for_save:
                    status = request.form.get(f"status_{student['id']}")
                    if status in ("Present", "Absent"):
                        db.execute("""INSERT INTO attendance (student_id, attendance_date, status) VALUES (?, ?, ?)
                            ON CONFLICT(student_id, attendance_date) DO UPDATE SET status = excluded.status""",
                                   (student["id"], selected_date, status))
                db.commit()
                flash("Attendance saved successfully.", "success")
    query = "SELECT * FROM students"
    params = []
    if selected_section:
        query += " WHERE section = ?"
        params.append(selected_section)
    student_rows = db.execute(query + " ORDER BY name", params).fetchall()
    existing = db.execute("SELECT student_id, status FROM attendance WHERE attendance_date = ?", (selected_date,)).fetchall()
    statuses = {row["student_id"]: row["status"] for row in existing}
    sections = db.execute("SELECT DISTINCT section FROM students ORDER BY section").fetchall()
    return render_template("attendance.html", students=student_rows, statuses=statuses, selected_date=selected_date,
                           selected_section=selected_section, sections=sections)


@app.route("/reports")
@login_required
def reports():
    db = get_db()
    report_type = request.args.get("report_type", "daily")
    selected_date = request.args.get("date", date.today().isoformat())
    student_filter = request.args.get("student_id", "")
    department = request.args.get("department", "")
    year = request.args.get("year", "")
    section = request.args.get("section", "")
    status = request.args.get("status", "")
    query = """SELECT a.attendance_date, a.status, s.student_id, s.name, s.roll_number,
        s.department, s.year, s.section FROM attendance a JOIN students s ON s.id = a.student_id WHERE 1=1"""
    params = []
    if selected_date and report_type in ("daily", "date"):
        query += " AND a.attendance_date = ?"
        params.append(selected_date)
    if report_type == "monthly" and selected_date:
        query += " AND substr(a.attendance_date, 1, 7) = ?"
        params.append(selected_date[:7])
    if student_filter:
        query += " AND s.id = ?"
        params.append(student_filter)
    for field, value in (("department", department), ("year", year), ("section", section)):
        if value:
            query += f" AND s.{field} = ?"
            params.append(value)
    if status in ("Present", "Absent"):
        query += " AND a.status = ?"
        params.append(status)
    rows = db.execute(query + " ORDER BY a.attendance_date DESC, s.name", params).fetchall()
    students_list = db.execute("SELECT id, name, student_id FROM students ORDER BY name").fetchall()
    departments = db.execute("SELECT DISTINCT department FROM students ORDER BY department").fetchall()
    years = db.execute("SELECT DISTINCT year FROM students ORDER BY year").fetchall()
    sections = db.execute("SELECT DISTINCT section FROM students ORDER BY section").fetchall()
    return render_template("reports.html", rows=rows, report_type=report_type, selected_date=selected_date,
                           student_filter=student_filter, department=department, year=year, section=section,
                           status=status, students=students_list, departments=departments, years=years,
                           sections=sections)


@app.route("/profile")
@login_required
def profile():
    user = get_db().execute("SELECT username, full_name, role, created_at FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    return render_template("profile.html", user=user)


@app.errorhandler(404)
def page_not_found(error):
    return render_template("error.html", code=404, message="The page you requested was not found."), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template("error.html", code=500, message="Something went wrong. Please try again."), 500


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True)
