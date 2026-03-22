import os
import sqlite3
from flask import Flask, render_template, request, redirect
from werkzeug.utils import secure_filename
from datetime import datetime
import PyPDF2
import docx

app = Flask(__name__)

# ✅ Absolute path fix (IMPORTANT for Render)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
DB_PATH = os.path.join(BASE_DIR, 'database.db')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ✅ Ensure uploads folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            filepath TEXT,
            category TEXT,
            upload_date TEXT
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
    if request.method == 'POST':
        file = request.files['file']

        if file and file.filename != "":
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            file.save(filepath)

            text = extract_text(filepath)
            category = classify_text(text, filename)

            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT INTO files (filename, filepath, category, upload_date) VALUES (?, ?, ?, ?)",
                      (filename, filepath, category, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()

            return redirect('/dashboard')

    return render_template('upload.html')


@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM files")
    files = c.fetchall()
    conn.close()

    return render_template('dashboard.html', files=files)


if __name__ == '__main__':
    app.run(debug=True)