import os
from flask import Flask, request, render_template, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
import sqlite3
from datetime import datetime
from pathlib import Path

# -------------------- CONFIG --------------------
APP_DIR = Path(__file__).parent
UPLOAD_FOLDER = os.path.join(APP_DIR, "uploads")
DB_PATH = os.path.join(APP_DIR, "data.db")

# Make uploads folder safely
if not os.path.isdir(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")  # Set in Render

# -------------------- FLASK APP --------------------
app = Flask(__name__)
app.secret_key = "secret123"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# -------------------- DATABASE --------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            village TEXT,
            post TEXT,
            gp TEXT,
            pin TEXT,
            district TEXT,
            state TEXT,
            caste_file TEXT,
            income_file TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# -------------------- ROUTES --------------------

@app.route("/")
def home():
    return render_template("form.html")


@app.route("/submit", methods=["POST"])
def submit():
    # Get form values
    name = request.form.get("name")
    village = request.form.get("village")
    post = request.form.get("post")
    gp = request.form.get("gp")
    pin = request.form.get("pin")
    district = request.form.get("district")
    state = request.form.get("state")

    # Get files
    caste = request.files["caste"]
    income = request.files["income"]

    caste_name = secure_filename(caste.filename)
    income_name = secure_filename(income.filename)

    caste_path = os.path.join(UPLOAD_FOLDER, caste_name)
    income_path = os.path.join(UPLOAD_FOLDER, income_name)

    caste.save(caste_path)
    income.save(income_path)

    # Insert into DB
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO applications 
        (name, village, post, gp, pin, district, state, caste_file, income_file, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name, village, post, gp, pin, district, state,
        caste_name, income_name,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

    flash("Application submitted successfully!")
    return redirect(url_for("home"))


# -------------------- ADMIN --------------------

@app.route("/admin")
def admin_login():
    return render_template("admin_login.html")


@app.route("/admin/check", methods=["POST"])
def admin_check():
    password = request.form.get("password")
    if password != ADMIN_PASSWORD:
        return "Wrong Password!"
    return redirect(url_for("dashboard"))


@app.route("/admin/dashboard")
def dashboard():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM applications ORDER BY id DESC")
    data = c.fetchall()
    conn.close()

    return render_template("dashboard.html", data=data)


# Download files
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# -------------------- REQUIRED FOR RENDER --------------------
# Render looks for `app` variable inside app.py
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
