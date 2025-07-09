from flask import Flask, render_template, request, send_file, send_from_directory
import csv
import os
import sqlite3
import io
from werkzeug.utils import secure_filename
import pandas as pd

app = Flask(__name__)

# Configuration for file uploads
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create uploads folder if not exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

CSV_FILE = "reports.csv"

# Ensure CSV exists with headers
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode="w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            "Full Name", "Email", "Date", "Time", "Shift", "Department",
            "Report Type", "Responsible Person", "Location", "Sub-location", "Hazard Description", "Filename"
        ])

# Ensure SQLite database exists
def init_db():
    conn = sqlite3.connect("reports.db")
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname TEXT,
        email TEXT,
        date TEXT,
        time TEXT,
        shift TEXT,
        department TEXT,
        report_type TEXT,
        responsible TEXT,
        location TEXT,
        sublocation TEXT,
        description TEXT,
        filename TEXT,
        file_blob BLOB,
        status TEXT DEFAULT 'Open'
    )''')
    conn.commit()
    conn.close()

init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_report_to_db(data, file_blob):
    conn = sqlite3.connect('reports.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO reports (
            fullname, email, date, time, shift, department, report_type,
            responsible, location, sublocation, description, filename, file_blob
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', data + [file_blob])
    conn.commit()
    conn.close()

from datetime import datetime

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        uploaded_file = request.files.get("file")
        filename = ""
        file_blob = None

        if uploaded_file and allowed_file(uploaded_file.filename):
            filename = secure_filename(uploaded_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(file_path)
            with open(file_path, "rb") as f:
                file_blob = f.read()

        data = [
            request.form.get("fullname"),
            request.form.get("email"),
            request.form.get("date"),
            request.form.get("time"),
            request.form.get("shift"),
            request.form.get("department"),
            request.form.get("report_type"),
            request.form.get("responsible"),
            request.form.get("location"),
            request.form.get("sublocation"),
            request.form.get("description"),
            filename
        ]

        # Save to CSV
        with open(CSV_FILE, mode="a", newline='') as file:
            writer = csv.writer(file)
            writer.writerow(data)

        # Save to DB
        save_report_to_db(data, file_blob)

        return "✅ Report submitted successfully! <br><a href='/'>Back to form</a>"

    return render_template("index.html", time=datetime.now().timestamp())

@app.route("/reports")
def show_reports():
    conn = sqlite3.connect("reports.db")
    c = conn.cursor()
    c.execute("SELECT id, fullname, email, date, time, shift, department, report_type, responsible, location, sublocation, description, filename, status FROM reports")
    rows = c.fetchall()
    headers = ["ID", "Full Name", "Email", "Date", "Time", "Shift", "Department", "Report Type", "Responsible Person for Compliance of Hazard", "Location", "Sub-location", "Description", "Attachment", "Status"]
    conn.close()
    return render_template("reports.html", headers=headers, data=rows)

@app.route("/close/<int:report_id>")
def close_report(report_id):
    conn = sqlite3.connect('reports.db')
    c = conn.cursor()
    c.execute("UPDATE reports SET status = 'Closed' WHERE id = ?", (report_id,))
    conn.commit()
    conn.close()
    return "<script>alert('✅ Report closed successfully!');window.location.href='/reports';</script>"

@app.route("/download-excel")
def download_excel():
    conn = sqlite3.connect("reports.db")
    df = pd.read_sql_query("""
        SELECT fullname, email, date, time, shift, department, report_type,
               responsible, location, sublocation, description, filename
        FROM reports
    """, conn)
    conn.close()

    # Create Excel in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Reports')
    output.seek(0)

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="Hazard_Reports.xlsx"
    )

@app.route("/download/<int:report_id>")
def download_file(report_id):
    conn = sqlite3.connect('reports.db')
    c = conn.cursor()
    c.execute("SELECT filename, file_blob FROM reports WHERE id = ?", (report_id,))
    row = c.fetchone()
    conn.close()

    if row and row[1]:
        return send_file(
            io.BytesIO(row[1]),
            download_name=row[0],
            as_attachment=True
        )
    else:
        return "File not found."

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/download-csv")
def download_csv():
    return send_file("reports.csv", as_attachment=True)

@app.route("/download-db")
def download_db():
    return send_file("reports.db", as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
