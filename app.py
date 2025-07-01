from flask import Flask, render_template, request, redirect
import csv
import os

app = Flask(__name__)

# Ensure the CSV file exists with headers
if not os.path.exists("reports.csv"):
    with open("reports.csv", mode="w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Full Name", "Email", "Date", "Time", "Shift", "Department",
                         "Report Type", "Location", "Sub-location", "Hazard Description"])

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
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
        ]
        
        with open("reports.csv", mode="a", newline='') as file:
            writer = csv.writer(file)
            writer.writerow(data)

        return "✅ Report submitted successfully! <br><a href='/'>Back to form</a>"

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
