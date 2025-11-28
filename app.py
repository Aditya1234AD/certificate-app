from flask import Flask, render_template, request
import sqlite3
import os

app = Flask(__name__)

# ---------------------------------------------------
# SAFE FOLDER CREATION (Render requires this)
# ---------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DB_DIR, exist_ok=True)

UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB_PATH = os.path.join(DB_DIR, "database.db")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ---------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------
def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                village TEXT,
                post TEXT,
                gp TEXT,
                pincode TEXT,
                district TEXT,
                state TEXT,
                caste_file TEXT,
                income_file TEXT,
                residence_file TEXT
            )
        """)

        conn.commit()
        conn.close()
        print("Database initialized successfully.")

    except Exception as e:
        print("DB ERROR:", e)


# Initialize DB once
init_db()


# ---------------------------------------------------
# ROUTES
# ---------------------------------------------------
@app.route("/")
def home():
    return "<h1>Flask App Running Successfully</h1>"


@app.route("/submit", methods=["POST"])
def submit():
    name = request.form.get("name")
    village = request.form.get("village")
    post = request.form.get("post")
    gp = request.form.get("gp")
    pincode = request.form.get("pincode")
    district = request.form.get("district")
    state = request.form.get("state")

    caste = request.files.get("caste")
    income = request.files.get("income")
    residence = request.files.get("residence")

    def save(file):
        if file and file.filename:
            save_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(save_path)
            return file.filename
        return None

    caste_file = save(caste)
    income_file = save(income)
    residence_file = save(residence)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        INSERT INTO applications 
        (name, village, post, gp, pincode, district, state, caste_file, income_file, residence_file)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, village, post, gp, pincode, district, state, caste_file, income_file, residence_file))

    conn.commit()
    conn.close()

    return "<h2>Submitted Successfully!</h2>"


# ---------------------------------------------------
# RUN APP
# ---------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
