import sqlite3

# Initialize the database and create table
conn = sqlite3.connect('reports.db')
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
    file_blob BLOB
)
''')

conn.commit()
conn.close()
