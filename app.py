import os
import sqlite3
from flask import Flask, render_template, request, redirect
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import session
import PyPDF2
import docx


app = Flask(__name__)
app.secret_key = "secret123"

# ✅ Absolute path fix (IMPORTANT for Render)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
DB_PATH = os.path.join(BASE_DIR, 'database.db')
print("Using DB at:", DB_PATH)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ✅ Ensure uploads folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')

    # Files table (add user_id)
    c.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            filepath TEXT,
            category TEXT,
            upload_date TEXT,
            user_id INTEGER
        )
    ''')

    conn.commit()
    conn.close()
init_db()

# ---------------- AI CLASSIFICATION ----------------
def classify_text(text, filename):
    text = text.lower()

    if any(word in text for word in ["education", "skills", "experience"]):
        return "Resume"
    elif any(word in text for word in ["invoice", "amount", "bill", "total"]):
        return "Invoice"
    elif any(word in text for word in ["chapter", "lecture", "notes", "topic"]):
        return "Notes"
    elif filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        return "Image"
    else:
        return "Others"

# ---------------- TEXT EXTRACTION ----------------
def extract_text(filepath):
    text = ""

    if filepath.endswith('.pdf'):
        try:
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ""
        except:
            pass

    elif filepath.endswith('.docx'):
        try:
            doc = docx.Document(filepath)
            for para in doc.paragraphs:
                text += para.text
        except:
            pass

    return text

# ---------------- ROUTES ----------------

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['GET', 'POST'])
def upload():

    # ✅ ADD THIS (login protection)
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        file = request.files['file']

        if file and file.filename != "":
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # ✅ FIXED TYPO
            file.save(filepath)

            text = extract_text(filepath)
            category = classify_text(text, filename)

            # ✅ GET USER ID
            user_id = session['user_id']

            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()

            # ✅ UPDATED QUERY (added user_id)
            c.execute("INSERT INTO files (filename, filepath, category, upload_date, user_id) VALUES (?, ?, ?, ?, ?)",
                      (filename, filepath, category, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))

            conn.commit()
            conn.close()

            return redirect('/dashboard')

    return render_template('upload.html')


@app.route('/dashboard')
def dashboard():

    # ✅ LOGIN PROTECTION
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # ✅ SHOW ONLY CURRENT USER FILES
    c.execute("SELECT * FROM files WHERE user_id=?", (user_id,))
    files = c.fetchall()

    conn.close()

    return render_template('dashboard.html', files=files)



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
        except:
            return "Username already exists!"

        conn.close()
        return redirect('/login')

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            return redirect('/dashboard')
        else:
            return "Invalid credentials!"

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


if __name__ == '__main__':
    app.run(debug=True)