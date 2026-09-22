# Student Attendance Automation System

## Project Overview

Student Attendance Automation System is a beginner-friendly college administration application for managing student records, marking daily attendance, and generating useful attendance reports. It replaces scattered manual registers with a single, searchable workspace for teachers and administrators.

## Features

- Secure password-hashed admin/teacher login and logout
- Protected dashboard and application routes
- Dashboard cards for student count, daily presence, absence, and overall attendance
- Student CRUD: add, edit, search, filter, and delete
- Duplicate Student ID and roll-number prevention
- Date and section-based attendance marking
- Present/Absent status with duplicate-safe updates
- Daily, date-wise, monthly, and student-wise reports
- Filters for student, date, department, year, section, and status context
- Automatic attendance percentage calculation
- Low attendance alerts for students below 75%
- SQLite database created automatically with safe demo data
- Responsive college-management interface

## Technologies Used

- Python
- Flask
- SQLite
- HTML
- CSS
- JavaScript

## System Architecture

The browser renders HTML/CSS/JavaScript pages and sends requests to the Flask backend. Flask validates input, applies authentication and business rules, and reads/writes data in SQLite.

**Frontend -> Flask Backend -> SQLite Database**

## Database Design

- `users`: login username, password hash, display name, and role.
- `students`: unique student ID and roll number plus contact and class details.
- `attendance`: student/date/status records with a unique constraint preventing duplicate attendance for the same student on the same date.

## Installation

```bash
git clone <repository-url>
cd Student-Attendance-Automation-System

python -m venv venv
```

Windows:

```powershell
venv\Scripts\activate
```

Install dependencies and run:

```bash
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000` in your browser. The SQLite database and demo records are created automatically on first launch.

## Demo Login

This local demo account is safe for development only:

- Username: `admin`
- Password: `admin123`

Change the credential implementation before using the application in production.

## Screenshots

Add screenshots to the `screenshots/` directory and link them here:

- `screenshots/dashboard.png` - Dashboard overview
- `screenshots/students.png` - Student directory
- `screenshots/attendance.png` - Attendance register
- `screenshots/reports.png` - Filtered report

## Future Enhancements

- Face recognition attendance
- QR code attendance
- Email/SMS notifications
- Excel/PDF reports
- Cloud database
- Student login
- Mobile application

## Author

**Makkena Surya Prakash**  
B.Tech CSE

## GitHub Commands

```bash
git init
git add .
git commit -m "Initial commit: student attendance automation system"
git branch -M main
git remote add origin https://github.com/suryaprakash-15/Student-Attendance-Automation-System.git
git push -u origin main
```

## Interview Explanation

This project is a Flask MVC-style web application. A teacher logs in through a protected session, manages students through CRUD routes, and records attendance through a date/section form. SQLite stores normalized users, students, and attendance tables. Unique constraints prevent duplicate identifiers and duplicate daily attendance. Reports use SQL joins and filters, while Python calculates attendance percentages and flags students below 75%.

## Common Interview Questions and Answers

1. **Why did you choose Flask?** Flask is lightweight, readable, and lets me understand routing, templates, sessions, and database access without hiding the fundamentals behind a large framework.
2. **Why SQLite?** SQLite is serverless and ideal for a small college application or portfolio demo. It can later be replaced with PostgreSQL with limited query-layer changes.
3. **How are passwords stored?** Passwords are stored as Werkzeug-generated hashes, never as plain text. Login verifies a submitted password against the hash.
4. **How are duplicate students prevented?** `student_id` and `roll_number` have `UNIQUE` constraints, and the Flask route catches integrity errors to show a friendly message.
5. **How is duplicate attendance prevented?** The attendance table has a unique `(student_id, attendance_date)` constraint. Saving attendance uses an upsert to update an existing daily record.
6. **How is attendance percentage calculated?** Present days are divided by total attendance records and multiplied by 100. A zero-record student safely receives 0%.
7. **How are pages protected?** A `login_required` decorator checks the session before allowing access to dashboard, student, attendance, report, and profile routes.
8. **How does the low attendance alert work?** A grouped SQL query calculates each student's present/total ratio and returns records below 75% for the dashboard.
9. **What validation is implemented?** Required fields, email shape, phone digits, date parsing, login credentials, and database uniqueness are validated.
10. **How would you scale this project?** I would move to PostgreSQL, add role-based permissions, CSRF protection, pagination, automated tests, exports, deployment configuration, and a student-facing mobile/API client.
