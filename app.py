from flask import Flask, render_template, request, redirect, session
import psycopg2
import os

app = Flask(__name__)
app.secret_key = "secret123"

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name TEXT,
        email TEXT,
        password TEXT,
        role TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id SERIAL PRIMARY KEY,
        title TEXT,
        description TEXT,
        salary TEXT,
        location TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id SERIAL PRIMARY KEY,
        user_name TEXT,
        job TEXT,
        company TEXT,
        salary TEXT,
        location TEXT,
        resume TEXT,
        status TEXT DEFAULT 'Applied'
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS interviews (
        id SERIAL PRIMARY KEY,
        application_id INTEGER,
        date TEXT,
        time TEXT,
        result TEXT
    )
    """)

    conn.commit()
    cur.close()
    conn.close()

init_db()

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            session['user'] = user[1]
            session['role'] = user[4]

            if user[4] == 'hr':
                return redirect('/hr_dashboard')
            else:
                return redirect('/candidate_dashboard')

        return "<h3>Invalid Email or Password ❌</h3>"

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        if cur.fetchone():
            cur.close()
            conn.close()
            return "<h3>Email already exists ❌</h3>"

        cur.execute(
            "INSERT INTO users (name,email,password,role) VALUES (%s,%s,%s,%s)",
            (name, email, password, role)
        )

        conn.commit()
        cur.close()
        conn.close()

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
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs")
    jobs = cur.fetchall()

    cur.execute("SELECT * FROM applications")
    apps = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('hr_dashboard.html', jobs=jobs, apps=apps)

@app.route('/post_job', methods=['GET', 'POST'])
def post_job():
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        title = request.form['title']
        desc = request.form['description']
        salary = request.form['salary']
        location = request.form['location']

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM jobs WHERE title=%s AND location=%s",
            (title, location)
        )
        if cur.fetchone():
            cur.close()
            conn.close()
            return "<h3>Job already posted ❌</h3>"

        cur.execute(
            "INSERT INTO jobs (title,description,salary,location) VALUES (%s,%s,%s,%s)",
            (title, desc, salary, location)
        )

        conn.commit()
        cur.close()
        conn.close()

        return redirect('/hr_dashboard')

    return render_template('post_job.html')

@app.route('/jobs')
def jobs():
    if 'user' not in session:
        return redirect('/login')

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs")
    jobs = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('jobs.html', jobs=jobs)

@app.route('/apply/<int:id>', methods=['GET', 'POST'])
def apply(id):
    if 'user' not in session:
        return redirect('/login')

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs WHERE id=%s", (id,))
    job = cur.fetchone()

    if request.method == 'POST':

        # STRICT DUPLICATE CHECK (ALL FIELDS)
        cur.execute(
            "SELECT * FROM applications WHERE user_name=%s AND job=%s AND location=%s AND salary=%s",
            (session['user'], job[1], job[4], job[3])
        )

        if cur.fetchone():
            cur.close()
            conn.close()
            return "<h3>You already applied for this job ❌</h3>"

        file = request.files.get('resume')

        if not file or file.filename == "":
            return "<h3>No file selected ❌</h3>"

        filename = file.filename
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        cur.execute(
            "INSERT INTO applications (user_name,job,company,salary,location,resume,status) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (session['user'], job[1], "Company", job[3], job[4], filename, "Applied")
        )

        conn.commit()
        cur.close()
        conn.close()

        return redirect('/applications')

    cur.close()
    conn.close()
    return render_template('apply.html', job=job)

@app.route('/applications')
def applications():
    if 'user' not in session:
        return redirect('/login')

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM applications WHERE user_name=%s", (session['user'],))
    apps = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('applications.html', apps=apps)

@app.route('/shortlist/<int:id>')
def shortlist(id):
    if 'user' not in session:
        return redirect('/login')

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE applications SET status='Shortlisted' WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()

    return redirect('/hr_dashboard')

@app.route('/interview/<int:id>', methods=['GET', 'POST'])
def interview(id):
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        date = request.form['date']
        time = request.form['time']

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO interviews (application_id,date,time,result) VALUES (%s,%s,%s,%s)",
            (id, date, time, "Scheduled")
        )

        cur.execute(
            "UPDATE applications SET status='Interview Scheduled' WHERE id=%s",
            (id,)
        )

        conn.commit()
        cur.close()
        conn.close()

        return redirect('/hr_dashboard')

    return render_template('interview.html', id=id)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# 👉 ADD HERE 👇
@app.route('/delete_duplicates')
def delete_duplicates():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM applications a
        USING applications b
        WHERE a.id > b.id
        AND a.user_name = b.user_name
        AND a.job = b.job
        AND a.salary = b.salary
        AND a.location = b.location
    """)

    conn.commit()
    cur.close()
    conn.close()

    return "Duplicates deleted ✅"
    
if __name__ == "__main__":
    app.run()