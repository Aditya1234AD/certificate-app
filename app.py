from flask import Flask, render_template, request, redirect, send_from_directory
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
            cert_type TEXT,
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
# CLIENT PAGE
# ---------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------
# FORM SUBMISSION
# ---------------------------------------------------
@app.route("/submit", methods=["POST"])
def submit_form():

    # Text Inputs
    cert_type = request.form.get("cert_type")
    name = request.form.get("name")
    village = request.form.get("village")
    post = request.form.get("post")
    gp = request.form.get("gp")
    pin = request.form.get("pin")
    district = request.form.get("district")
    state = request.form.get("state")

    # Files
    aadhar = request.files.get("aadhaar")
    father_aadhar = request.files.get("father_aadhaar")
    applicant_photo = request.files.get("photo")   # FIXED NAME
    ror = request.files.get("ror")                 # OPTIONAL

    # Save Aadhaar
    aadhar_filename = aadhar.filename
    aadhar.save(os.path.join(UPLOAD_FOLDER, aadhar_filename))

    # Save Father's Aadhaar
    father_filename = father_aadhar.filename
    father_aadhar.save(os.path.join(UPLOAD_FOLDER, father_filename))

    # Save Applicant Photo
    photo_filename = applicant_photo.filename
    applicant_photo.save(os.path.join(UPLOAD_FOLDER, photo_filename))

    # Save ROR only if uploaded
    if ror and ror.filename != "":
        ror_filename = ror.filename
        ror.save(os.path.join(UPLOAD_FOLDER, ror_filename))
    else:
        ror_filename = None

    # Store in database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO applications 
        (cert_type, name, village, post, gp, pin, district, state,
         aadhar_file, ror_file, father_aadhar_file, applicant_photo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (cert_type, name, village, post, gp, pin, district, state,
          aadhar_filename, ror_filename, father_filename, photo_filename))
    conn.commit()
    conn.close()

    return redirect("/thanks")


# ---------------------------------------------------
# THANK YOU PAGE
# ---------------------------------------------------
@app.route("/thanks")
def thanks():
    return render_template("thanks.html")


# ---------------------------------------------------
# ADMIN PAGE
# ---------------------------------------------------
@app.route("/admin")
def admin_page():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM applications")
    data = c.fetchall()
    conn.close()
    return render_template("admin.html", applications=data)


# ---------------------------------------------------
# SERVE UPLOADED FILES
# ---------------------------------------------------
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# ---------------------------------------------------
# RUN
# ---------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
