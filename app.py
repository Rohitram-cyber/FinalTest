import os, csv, sqlite3, io
from flask import Flask, render_template, request, redirect, url_for, send_file, send_from_directory, flash
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from datetime import datetime
import pandas as pd

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "defaultsecret")

# Email configuration via environment variables
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
    MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD"),
    MAIL_DEFAULT_SENDER=('JSW Hazard Report', os.environ.get("MAIL_USERNAME"))
)
mail = Mail(app)

# Upload settings
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'docx'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# CSV setup
CSV_FILE = "reports.csv"
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "Full Name", "Mobile No", "Date", "Time", "Shift", "Department",
            "Report Type", "Concern Department for Compliance of Hazard", "Location", "Sub-location",
            "Hazard Description", "filename"
        ])

# DB setup
def init_db():
    with sqlite3.connect("reports.db") as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fullname TEXT, mobile TEXT, email TEXT, date TEXT, time TEXT,
                shift TEXT, department TEXT, report_type TEXT,
                responsible TEXT, location TEXT, sublocation TEXT,
                description TEXT, filename TEXT, file_blob BLOB,
                status TEXT DEFAULT 'Open'
            )
        ''')
init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_report_to_db(data, file_blob):
    with sqlite3.connect("reports.db") as conn:
        conn.execute('''
            INSERT INTO reports (
                fullname, mobile, date, time, shift, department, report_type,
                concern, location, sublocation, description, filename, file_blob
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data + [file_blob])

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

        # Form data collection
        form_data = {
            "fullname": request.form.get("fullname", "").strip(),
            "mobile": request.form.get("mobile", "").strip(),
            "date": request.form.get("date", "").strip(),
            "time": request.form.get("time", "").strip(),
            "shift": request.form.get("shift", "").strip(),
            "department": request.form.get("department", "").strip(),
            "report_type": request.form.get("report_type", "").strip(),
            "responsible": request.form.get("responsible", "").strip(),
            "location": request.form.get("location", "").strip(),
            "sublocation": request.form.get("sublocation", "").strip(),
            "description": request.form.get("description", "").strip(),
            "filename": filename
        }

        # Save to CSV
        with open(CSV_FILE, "a", newline='') as file:
            writer = csv.writer(file)
            writer.writerow(form_data.values())

        # Save to DB
        save_report_to_db(list(form_data.values()), file_blob)

        # Send Email
        try:
            body = "\n".join([f"{k.replace('_', ' ').title()}: {v}" for k, v in form_data.items() if k != "filename"])
            msg = Message(subject="New Hazard Report Submission",
                          recipients=["rohit29ram@gmail.com"],
                          body=f"New Hazard Report Submitted:\n\n{body}")
            if uploaded_file:
                uploaded_file.stream.seek(0)
                msg.attach(uploaded_file.filename, uploaded_file.content_type, uploaded_file.read())
            mail.send(msg)
        except Exception as e:
            print("Error sending email:", e)

        flash("✅Report submitted successfully!")
        return redirect(url_for("index"))

    return render_template("index.html", time=datetime.now().timestamp())

@app.route("/reports")
def show_reports():
    with sqlite3.connect("reports.db") as conn:
        rows = conn.execute("""
            SELECT id, fullname, mobile, date, time, shift, department,
               report_type, responsible, location, sublocation,
               description, filename, status
            FROM reports
        """).fetchall()
    headers = ["Full Name", "Mobile No.", "Date", "Time", "Shift", "Department", "Report Type", "Concern Department for Compliance of Hazard", "Location", "Sub-location", "Description", "Attachment", "Status"]
    return render_template("reports.html", headers=headers, data=rows)

@app.route("/close/<int:report_id>")
def close_report(report_id):
    with sqlite3.connect("reports.db") as conn:
        conn.execute("UPDATE reports SET status = 'Closed' WHERE id = ?", (report_id,))
    flash("✅ Report closed successfully.")
    return redirect(url_for("show_reports"))

@app.route("/download-excel")
def download_excel():
    with sqlite3.connect("reports.db") as conn:
        df = pd.read_sql_query("SELECT * FROM reports", conn)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Reports')
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="Hazard_Reports.xlsx")

@app.route("/download/<int:report_id>")
def download_file(report_id):
    with sqlite3.connect("reports.db") as conn:
        row = conn.execute("SELECT filename, file_blob FROM reports WHERE id = ?", (report_id,)).fetchone()
    if row and row[1]:
        return send_file(io.BytesIO(row[1]), download_name=row[0], as_attachment=True)
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
