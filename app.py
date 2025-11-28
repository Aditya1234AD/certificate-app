import os
from flask import Flask, request, render_template, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
import sqlite3
from datetime import datetime

# ------------------- CONFIG (RENDER SAFE) -------------------

# Store uploads & database on Render disk
UPLOAD_FOLDER = "/var/data/uploads"
DB_FOLDER = "/var/data"
DB_PATH = "/var/data/data.db"

# Create /var/data first
if not os.path.exists(DB_FOLDER):
    try:
        os.makedirs(DB_FOLDER)
    except:
        pass

# Create uploads folder
if not os.path.exists(UPLOAD_FOLDER):
    try:
        os.makedirs(UPLOAD_FOLDER)
    except:
        pass

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")  # set this in Render


# ------------------- FLASK APP -------------------
app = Flask(__name__)
app.secret_key = "mysecretkey"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ------------------- DATABASE -------------------
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


# ------------------- ROUTES -------------------

@app.route("/")
def form_page():
    return render_template("form.html")


@app.route("/submit", methods=["POST"])
def submit():
    # Read text inputs
    name = request.form.get("name")
    village = request.form.get("village")
    post = request.form.get("post")
    gp = request.form.get("gp")
    pin = request.form.get("pin")
    district = request.form.get("district")
    state = request.form.get("state")

    # Read uploaded files
    caste_file = request.files["caste"]
    income_file = request.files["income"]

    caste_name = secure_filename(caste_file.filename)
    income_name = secure_filename(income_file.filename)

    caste_path = os.path.join(UPLOAD_FOLDER, caste_name)
    income_path = os.path.join(UPLOAD_FOLDER, income_name)

    caste_file.save(caste_path)
    income_file.save(income_path)

    # Save data into database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO applications
        (name, village, post, gp, pin, district, state,
         caste_file, income_file, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name, village, post, gp, pin, district, state,
        caste_name, income_name,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

    flash("Application Submitted Successfully!")
    return redirect(url_for("form_page"))


# ------------------- ADMIN -------------------

@app.route("/admin")
def admin_login():
    return render_template("admin_login.html")


@app.route("/admin/check", methods=["POST"])
def admin_check():
    password = request.form.get("password")
    if password != ADMIN_PASSWORD:
        return "Wrong Password!"
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/dashboard")
def admin_dashboard():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM applications ORDER BY id DESC")
    data = c.fetchall()
    conn.close()

    return render_template("dashboard.html", data=data)


# ------------------- DOWNLOAD FILE -------------------
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# ------------------- REQUIRED FOR RENDER -------------------
# Start command will be `python app:app`
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
