from flask import Flask, render_template, request, redirect
import sqlite3
import os

app = Flask(__name__)

# ---------------------------------------------------
# SAFE DIRECTORIES FOR RENDER
# ---------------------------------------------------
UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DB_DIR, exist_ok=True)

DB_PATH = os.path.join(DB_DIR, "applications.db")


# ---------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------
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
            aadhar_file TEXT,
            ror_file TEXT,
            father_aadhar_file TEXT,
            applicant_photo TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()


# ---------------------------------------------------
# ROUTES
# ---------------------------------------------------

# Client page
@app.route("/")
def index():
    return render_template("index.html")


# Handle form submission
@app.route("/submit", methods=["POST"])
def submit_form():

    # 1. Receive input fields
    name = request.form.get("name")
    village = request.form.get("village")
    post = request.form.get("post")
    gp = request.form.get("gp")
    pin = request.form.get("pin")
    district = request.form.get("district")
    state = request.form.get("state")

    # 2. Receive files
    aadhar = request.files.get("aadhar")
    ror = request.files.get("ror")
    father_aadhar = request.files.get("father_aadhar")
    applicant_photo = request.files.get("applicant_photo")

    # 3. Save files to /tmp/uploads
    aadhar_path = os.path.join(app.config["UPLOAD_FOLDER"], aadhar.filename)
    ror_path = os.path.join(app.config["UPLOAD_FOLDER"], ror.filename)
    father_path = os.path.join(app.config["UPLOAD_FOLDER"], father_aadhar.filename)
    photo_path = os.path.join(app.config["UPLOAD_FOLDER"], applicant_photo.filename)

    aadhar.save(aadhar_path)
    ror.save(ror_path)
    father_aadhar.save(father_path)
    applicant_photo.save(photo_path)

    # 4. Save data in SQLite
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO applications
        (name, village, post, gp, pin, district, state,
         aadhar_file, ror_file, father_aadhar_file, applicant_photo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, village, post, gp, pin, district, state,
          aadhar.filename, ror.filename, father_aadhar.filename, applicant_photo.filename))
    conn.commit()
    conn.close()

    return redirect("/thanks")


# Thank you page
@app.route("/thanks")
def thanks():
    return render_template("thanks.html")


# Admin Page → show all uploads + details
@app.route("/admin")
def admin_page():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM applications")
    data = c.fetchall()
    conn.close()
    return render_template("admin.html", applications=data, upload_path=UPLOAD_FOLDER)


# ---------------------------------------------------
# Run the app
# ---------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
