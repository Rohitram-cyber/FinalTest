import os, csv, sqlite3, io
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from datetime import datetime, timedelta
import pytz
import pandas as pd

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "defaultsecret")

# Email Configuration
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
    MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD"),
    MAIL_DEFAULT_SENDER=('JSW Hazard Report', os.environ.get("MAIL_USERNAME"))
)
mail = Mail(app)

# Upload Config
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ✅ DB Initialization
def init_db():
    with sqlite3.connect("reports.db") as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fullname TEXT, mobile TEXT, date TEXT, time TEXT,
                shift TEXT, department TEXT, report_type TEXT,
                responsible TEXT, location TEXT, sublocation TEXT,
                description TEXT, filename TEXT, file_blob BLOB,
                status TEXT DEFAULT 'Open',
                closure_filename TEXT,
                closure_blob BLOB,
                closure_comment TEXT
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
                responsible, location, sublocation, description,
                filename, file_blob
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data + [file_blob])

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        uploaded_file = request.files.get("file")
        filename, file_blob = "", None

        if uploaded_file and allowed_file(uploaded_file.filename):
            filename = secure_filename(uploaded_file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(path)
            with open(path, "rb") as f:
                file_blob = f.read()

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

        try:
            ist = pytz.timezone("Asia/Kolkata")
            submitted = ist.localize(datetime.strptime(f"{form_data['date']} {form_data['time']}", "%Y-%m-%d %H:%M"))
            now = datetime.now(ist)
            if submitted > now + timedelta(minutes=1):
                flash("⚠️ Future date/time not allowed.")
                return redirect(url_for("index"))
            if (now - submitted).days > 7:
                flash("⚠️ Only reports from the past 7 days are allowed.")
                return redirect(url_for("index"))
        except Exception:
            flash("⚠️ Invalid date or time format.")
            return redirect(url_for("index"))

        with open("reports.csv", "a", newline='') as f:
            csv.writer(f).writerow(form_data.values())

        save_report_to_db(list(form_data.values()), file_blob)

        try:
            body = "\n".join([f"{k.replace('_', ' ').title()}: {v}" for k, v in form_data.items() if k != "filename"])
            msg = Message("New Hazard Report Submission", recipients=["rohit29ram@gmail.com"], body=body)
            if uploaded_file:
                uploaded_file.stream.seek(0)
                msg.attach(uploaded_file.filename, uploaded_file.content_type, uploaded_file.read())
            mail.send(msg)
        except Exception as e:
            print("Email Error:", e)

        flash("✅ Report submitted successfully!")
        return redirect(url_for("index"))

    return render_template("index.html", time=datetime.now().timestamp())

@app.route("/reports")
def show_reports():
    with sqlite3.connect("reports.db") as conn:
        rows = conn.execute("""
            SELECT id, fullname, mobile, date, time, shift, department,
                   report_type, responsible, location, sublocation,
                   description, filename, status,
                   closure_filename, closure_blob, closure_comment
            FROM reports
        """).fetchall()

    headers = [
        "ID", "Full Name", "Mobile", "Date", "Time", "Shift", "Department",
        "Report Type", "Concern Dept", "Location", "Sub-location",
        "Description", "Attachment", "Status", "Closure Evidence", "Closure Comment"
    ]

    return render_template("reports.html", headers=headers, data=rows)

# ✅ Route for Closing Report
@app.route("/close/<int:report_id>", methods=["GET", "POST"])
def close_report(report_id):
    if request.method == "POST":
        file = request.files.get("closure_file")
        closure_comment = request.form.get("closure_comment", "").strip()

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_blob = file.read()

            print("CLOSURE FILE NAME:", filename)
            print("CLOSURE FILE SIZE:", len(file_blob))
            print(f"[DEBUG] Closing report ID: {report_id}")
            print(f"[DEBUG] Closure Filename: {filename}")
            print(f"[DEBUG] File Size: {len(file_blob)}")
            print(f"[DEBUG] Closure Comment: {closure_comment}")

            with sqlite3.connect("reports.db") as conn:
                conn.execute("""
                    UPDATE reports SET
                        status = 'Closed',
                        closure_filename = ?,
                        closure_blob = ?,
                        closure_comment = ?
                    WHERE id = ?
                """, (filename, file_blob, closure_comment, report_id))
            flash("✅ Report closed successfully with closure comment.")
        else:
            flash("⚠️ Please upload a valid file.")
        return redirect(url_for("show_reports"))

    return '''
    <h3>Upload Closure File & Comment</h3>
    <form method="POST" enctype="multipart/form-data">
        <label>Closure File:</label><br>
        <input type="file" name="closure_file" required><br><br>
        <label>Closure Comment:</label><br>
        <textarea name="closure_comment" rows="4" cols="50" required></textarea><br><br>
        <button type="submit">Upload & Close Report</button>
    </form>
    '''

# ✅ Debugging Route
@app.route("/debug/<int:report_id>")
def debug_report(report_id):
    with sqlite3.connect("reports.db") as conn:
        row = conn.execute("""
            SELECT id, status, closure_filename, closure_comment, length(closure_blob)
            FROM reports WHERE id = ?
        """, (report_id,)).fetchone()
    return f"<pre>{row}</pre>"

@app.route("/download/<int:report_id>")
def download_file(report_id):
    mode = request.args.get("mode", "download")
    with sqlite3.connect("reports.db") as conn:
        row = conn.execute("SELECT filename, file_blob FROM reports WHERE id = ?", (report_id,)).fetchone()
    if row and row[1]:
        return send_file(io.BytesIO(row[1]), download_name=row[0], as_attachment=(mode != "view"))
    return "File not found."

@app.route("/download-closure/<int:report_id>")
def download_closure_file(report_id):
    mode = request.args.get("mode", "download")
    with sqlite3.connect("reports.db") as conn:
        row = conn.execute("SELECT closure_filename, closure_blob FROM reports WHERE id = ?", (report_id,)).fetchone()
    if row and row[1]:
        return send_file(io.BytesIO(row[1]), download_name=row[0], as_attachment=(mode != "view"))
    return "Closure file not found.", 404

@app.route("/download-excel")
def download_excel():
    with sqlite3.connect("reports.db") as conn:
        df = pd.read_sql_query("SELECT * FROM reports", conn)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Reports')
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="Hazard_Reports.xlsx")

@app.route("/download-csv")
def download_csv():
    return send_file("reports.csv", as_attachment=True)

@app.route("/download-db")
def download_db():
    return send_file("reports.db", as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
