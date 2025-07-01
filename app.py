from flask import Flask, render_template, request, redirect, send_from_directory
import sqlite3, os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def init_db():
    conn = sqlite3.connect('hazards.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS hazards (
            full_name TEXT,
            email TEXT,
            date TEXT,
            time TEXT,
            shift TEXT,
            department TEXT,
            report_type TEXT,
            responsible_person TEXT,
            location TEXT,
            sub_location TEXT,
            description TEXT,
            filename TEXT
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('hazards.db')
    reports = conn.execute('SELECT * FROM hazards').fetchall()
    conn.close()
    return render_template('index.html', reports=reports)

@app.route('/report', methods=['POST'])
def report():
    file = request.files['file']
    if not file or file.filename == '':
        return "File upload is required.", 400

    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    data = (
        request.form['full_name'],
        request.form.get('email', ''),
        request.form['date'],
        request.form['time'],
        request.form['shift'],
        request.form['department'],
        request.form['report_type'],
        request.form['responsible_person'],
        request.form['location'],
        request.form['sub_location'],
        request.form['description'],
        filename
    )

    conn = sqlite3.connect('hazards.db')
    conn.execute('''
        INSERT INTO hazards (
            full_name, email, date, time, shift, department, report_type,
            responsible_person, location, sub_location, description, filename
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', data)
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
