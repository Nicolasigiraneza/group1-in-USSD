from flask import Flask, request, Response
from datetime import datetime
import mysql.connector

app = Flask(__name__)

# MySQL configuration
MYSQL_HOST = 'ballast.proxy.rlwy.net'  # or your MySQL server address
MYSQL_USER = 'root'       # your MySQL username
MYSQL_PASSWORD = 'AiejrHXMLMFtHmeLNfTwoDDkEGFMUqRd'  # your MySQL password
MYSQL_DATABASE = 'railway'  # your MySQL database name

# Helper to get student ID by phone number
def get_student_id_by_phone(phone):
    conn = mysql.connector.connect(
        host=MYSQL_HOST, 
        user=MYSQL_USER, 
        password=MYSQL_PASSWORD, 
        database=MYSQL_DATABASE
    )
    c = conn.cursor()
    c.execute('SELECT id FROM students WHERE phone_number = %s', (phone,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

# Mark attendance
def mark_attendance(student_id, date):
    conn = mysql.connector.connect(
        host=MYSQL_HOST, 
        user=MYSQL_USER, 
        password=MYSQL_PASSWORD, 
        database=MYSQL_DATABASE
    )
    c = conn.cursor()
    try:
        c.execute('INSERT INTO attendance (student_id, date, status) VALUES (%s, %s, %s)', (student_id, date, 'Present'))
        conn.commit()
        conn.close()
        return True
    except mysql.connector.IntegrityError:
        conn.close()
        return False

# Check attendance
def check_attendance(student_id, date):
    conn = mysql.connector.connect(
        host=MYSQL_HOST, 
        user=MYSQL_USER, 
        password=MYSQL_PASSWORD, 
        database=MYSQL_DATABASE
    )
    c = conn.cursor()
    c.execute('SELECT status FROM attendance WHERE student_id = %s AND date = %s', (student_id, date))
    result = c.fetchone()
    conn.close()
    return result[0] if result else "Absent"

# Get attendance list for a date
def get_attendance_by_date(date):
    conn = mysql.connector.connect(
        host=MYSQL_HOST, 
        user=MYSQL_USER, 
        password=MYSQL_PASSWORD, 
        database=MYSQL_DATABASE
    )
    c = conn.cursor()
    c.execute('''
        SELECT s.name, s.phone_number FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE a.date = %s
    ''', (date,))
    result = c.fetchall()
    conn.close()
    return [f"{name} ({phone})" for name, phone in result]

# STUDENT USSD
@app.route('/student-ussd', methods=['POST'])
def student_ussd():
    phone_number = request.form.get("phoneNumber")
    text = request.form.get("text").strip()

    student_id = get_student_id_by_phone(phone_number)
    today = datetime.today().strftime('%Y-%m-%d')

    if text == "":
        response = "CON Welcome to Class Attendance:\n1. Mark Attendance\n2. Check Attendance Status\n3. Exit"
    elif text == "1":
        if not student_id:
            response = "END You are not registered. Contact admin."
        elif check_attendance(student_id, today) == "Present":
            response = "END Attendance already marked today."
        else:
            success = mark_attendance(student_id, today)
            if success:
                response = "END Attendance marked successfully."
            else:
                response = "END Failed to mark attendance. Try again."
    elif text == "2":
        if not student_id:
            response = "END You are not registered."
        else:
            status = check_attendance(student_id, today)
            response = f"END Your attendance status for today: {status}."
    elif text == "3":
        response = "END Goodbye!"
    else:
        response = "END Invalid option."

    return Response(response, mimetype="text/plain")


# ADMIN USSD
@app.route('/admin-ussd', methods=['POST'])
def admin_ussd():
    text = request.form.get("text").strip()
    parts = text.split("*")

    if text == "":
        response = "CON Admin Menu:\n1. View Today's Attendance\n2. View Attendance by Date\n3. Exit\n4. Add New Student"

    elif parts[0] == "1":
        today = datetime.today().strftime('%Y-%m-%d')
        attendees = get_attendance_by_date(today)
        if attendees:
            response = "END Today's Attendance:\n" + "\n".join(attendees)
        else:
            response = "END No attendance records for today."

    elif parts[0] == "2":
        if len(parts) == 1:
            response = "CON Enter date (YYYY-MM-DD):"
        elif len(parts) == 2:
            date_input = parts[1]
            attendees = get_attendance_by_date(date_input)
            if attendees:
                response = f"END Attendance on {date_input}:\n" + "\n".join(attendees)
            else:
                response = f"END No records found for {date_input}."
        else:
            response = "END Invalid input."

    elif parts[0] == "3":
        response = "END Goodbye!"

    elif parts[0] == "4":
        if len(parts) == 1:
            response = "CON Enter student name:"
        elif len(parts) == 2:
            response = "CON Enter phone number:"
        elif len(parts) == 3:
            name = parts[1].strip()
            phone = parts[2].strip()

            # Insert new student
            conn = mysql.connector.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DATABASE
            )
            c = conn.cursor()
            try:
                c.execute("INSERT INTO students (name, phone_number) VALUES (%s, %s)", (name, phone))
                conn.commit()
                response = f"END Student {name} added successfully."
            except mysql.connector.Error as e:
                response = "END Failed to add student. May already exist."
            finally:
                conn.close()
        else:
            response = "END Invalid input."

    else:
        response = "END Invalid option."

    return Response(response, mimetype="text/plain")


if __name__ == '__main__':
    app.run(port=5000)
