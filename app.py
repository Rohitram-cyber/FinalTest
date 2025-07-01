from flask import Flask, render_template, request, send_file
import csv
import os
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
        writer.writerow(["Full Name", "Email", "Date", "Time", "Shift", "Department",
                         "Report Type", "Location", "Sub-location", "Hazard Description", "Filename"])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        uploaded_file = request.files.get("file")
        filename = ""

        # Save file if present and allowed
        if uploaded_file and allowed_file(uploaded_file.filename):
            filename = secure_filename(uploaded_file.filename)
            uploaded_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        data = [
            request.form.get("fullname"),
            request.form.get("email"),
            request.form.get("date"),
            request.form.get("time"),
            request.form.get("shift"),
            request.form.get("department"),
            request.form.get("report_type"),
            request.form.get("location"),
            request.form.get("sublocation"),
            request.form.get("description"),
            filename
        ]

        with open(CSV_FILE, mode="a", newline='') as file:
            writer = csv.writer(file)
            writer.writerow(data)

        return "✅ Report submitted successfully! <br><a href='/'>Back to form</a>"

    return render_template("index.html")


@app.route("/reports")
def show_reports():
    with open(CSV_FILE, mode="r") as file:
        reader = csv.reader(file)
        rows = list(reader)
        headers = rows[0]
        data = rows[1:]
    return render_template("reports.html", headers=headers, data=data)

@app.route("/download-excel")
def download_excel():
    csv_path = CSV_FILE
    excel_path = "reports.xlsx"

    try:
        # Convert CSV to Excel
        df = pd.read_csv(csv_path)
        df.to_excel(excel_path, index=False)

        return send_file(
            excel_path,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="Hazard_Reports.xlsx"
        )
    except Exception as e:
        return f"Error generating Excel file: {str(e)}"

# Serve uploaded files (for report view/download)
from flask import send_from_directory

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
