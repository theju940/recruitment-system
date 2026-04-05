from flask import Flask, render_template, request, redirect, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "secret123"

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db():
    return sqlite3.connect("database.db")

def init_db():
    conn = get_db()

    conn.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        password TEXT,
        role TEXT
    )
    ''')

    conn.execute('''
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        salary TEXT,
        location TEXT
    )
    ''')

    conn.execute('''
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        job TEXT,
        company TEXT,
        salary TEXT,
        location TEXT,
        resume TEXT,
        status TEXT DEFAULT 'Applied'
    )
    ''')

    conn.execute('''
    CREATE TABLE IF NOT EXISTS interviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER,
        date TEXT,
        time TEXT,
        result TEXT
    )
    ''')

    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        ).fetchone()

        if user:
            session['user'] = user[1]
            session['role'] = user[4]

            if user[4] == 'hr':
                return redirect('/hr_dashboard')
            else:
                return redirect('/candidate_dashboard')

        return "<h3>Invalid Email or Password ❌</h3>"

    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        conn = get_db()
        conn.execute(
            "INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
            (name, email, password, role)
        )
        conn.commit()

        return redirect('/login')

    return render_template('register.html')

@app.route('/candidate_dashboard')
def candidate_dashboard():
    if 'user' not in session:
        return redirect('/login')
    return render_template('candidate_dashboard.html')

@app.route('/hr_dashboard')
def hr_dashboard():
    if 'user' not in session:
        return redirect('/login')

    conn = get_db()
    jobs = conn.execute("SELECT * FROM jobs").fetchall()
    apps = conn.execute("SELECT * FROM applications").fetchall()
    return render_template('hr_dashboard.html', jobs=jobs, apps=apps)

@app.route('/post_job', methods=['GET','POST'])
def post_job():
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        title = request.form['title']
        desc = request.form['description']
        salary = request.form['salary']
        location = request.form['location']

        conn = get_db()
        conn.execute(
            "INSERT INTO jobs (title,description,salary,location) VALUES (?,?,?,?)",
            (title, desc, salary, location)
        )
        conn.commit()

        return redirect('/hr_dashboard')

    return render_template('post_job.html')

@app.route('/jobs')
def jobs():
    if 'user' not in session:
        return redirect('/login')

    conn = get_db()
    jobs = conn.execute("SELECT * FROM jobs").fetchall()
    return render_template('jobs.html', jobs=jobs)

@app.route('/apply/<int:id>', methods=['GET','POST'])
def apply(id):
    if 'user' not in session:
        return redirect('/login')

    conn = get_db()
    job = conn.execute("SELECT * FROM jobs WHERE id=?", (id,)).fetchone()

    if request.method == 'POST':
        file = request.files['resume']
        filename = file.filename
        file.save(os.path.join(UPLOAD_FOLDER, filename))

        conn.execute(
            "INSERT INTO applications (user,job,company,salary,location,resume,status) VALUES (?,?,?,?,?,?,?)",
            (session['user'], job[1], "Company", job[3], job[4], filename, "Applied")
        )
        conn.commit()

        return redirect('/applications')

    return render_template('apply.html', job=job)

@app.route('/applications')
def applications():
    if 'user' not in session:
        return redirect('/login')

    conn = get_db()
    apps = conn.execute(
        "SELECT * FROM applications WHERE user=?",
        (session['user'],)
    ).fetchall()

    return render_template('applications.html', apps=apps)

@app.route('/shortlist/<int:id>')
def shortlist(id):
    if 'user' not in session:
        return redirect('/login')

    conn = get_db()
    conn.execute("UPDATE applications SET status='Shortlisted' WHERE id=?", (id,))
    conn.commit()
    return redirect('/hr_dashboard')

@app.route('/interview/<int:id>', methods=['GET','POST'])
def interview(id):
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        date = request.form['date']
        time = request.form['time']

        conn = get_db()
        conn.execute(
            "INSERT INTO interviews (application_id,date,time,result) VALUES (?,?,?,?)",
            (id, date, time, "Pending")
        )
        conn.commit()
        return redirect('/hr_dashboard')

    return render_template('interview.html', id=id)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == "__main__":
    app.run()