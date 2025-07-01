from flask import Flask, render_template, request, redirect, flash
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        date = request.form.get('date')
        time = request.form.get('time')
        shift = request.form.get('shift')
        department = request.form.get('department')
        report_type = request.form.get('report_type')
        location = request.form.get('location')
        sub_location = request.form.get('sub_location')
        description = request.form.get('description')

        if not full_name:
            flash('Full Name is required!', 'danger')
            return redirect('/')

        file = request.files.get('file')
        filename = ''
        if file and file.filename != '':
            filename = datetime.now().strftime("%Y%m%d_%H%M%S_") + secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        flash('Hazard report submitted successfully!', 'success')
        return redirect('/')

    return render_template("index.html")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)  # Important for Render
