from flask import Flask, render_template, request, redirect, send_from_directory, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for flash messages

# ---------------------------------------------------
# SAFE DIRECTORIES
# ---------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

# If 'uploads' exists but is not a directory, remove it
if os.path.exists(UPLOAD_FOLDER) and not os.path.isdir(UPLOAD_FOLDER):
    os.remove(UPLOAD_FOLDER)

# Now safely create the uploads directory
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

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
            mobile TEXT,
            village TEXT,
            post TEXT,
            gp TEXT,
            pin TEXT,
            district TEXT,
            state TEXT,
            aadhar_file TEXT,
            ror_file TEXT,
            father_aadhar_file TEXT,
            applicant_photo TEXT,
            status TEXT
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
    try:
        # Text Inputs
        cert_type = request.form.get("cert_type")
        name = request.form.get("name")
        mobile = request.form.get("mobile")
        village = request.form.get("village")
        post = request.form.get("post")
        gp = request.form.get("gp")
        pin = request.form.get("pin")
        district = request.form.get("district")
        state = request.form.get("state")

        # Files
        aadhar = request.files.get("aadhaar")
        father_aadhar = request.files.get("father_aadhaar")
        applicant_photo = request.files.get("photo")
        ror = request.files.get("ror")  # Optional

        # Save files safely
        aadhar_filename = os.path.join(app.config["UPLOAD_FOLDER"], aadhar.filename)
        aadhar.save(aadhar_filename)

        father_filename = os.path.join(app.config["UPLOAD_FOLDER"], father_aadhar.filename)
        father_aadhar.save(father_filename)

        photo_filename = os.path.join(app.config["UPLOAD_FOLDER"], applicant_photo.filename)
        applicant_photo.save(photo_filename)

        if ror and ror.filename != "":
            ror_filename = os.path.join(app.config["UPLOAD_FOLDER"], ror.filename)
            ror.save(ror_filename)
        else:
            ror_filename = None

        # Insert into database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO applications 
            (cert_type, name, mobile, village, post, gp, pin, district, state,
             aadhar_file, ror_file, father_aadhar_file, applicant_photo, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (cert_type, name, mobile, village, post, gp, pin, district, state,
              os.path.basename(aadhar_filename),
              os.path.basename(ror_filename) if ror_filename else None,
              os.path.basename(father_filename),
              os.path.basename(photo_filename),
              'Pending'))
        conn.commit()
        conn.close()

        flash("Application submitted successfully!", "success")
        return redirect("/thanks")

    except Exception as e:
        print("Error during form submission:", e)
        flash("Error submitting application. Please try again.", "danger")
        return redirect("/")

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
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM applications")
        data = c.fetchall()
        conn.close()
        return render_template("admin.html", applications=data)
    except Exception as e:
        print("Error loading admin page:", e)
        return "Error loading admin page. Check server logs."

# ---------------------------------------------------
# ADMIN — STATUS UPDATE
# ---------------------------------------------------
@app.route('/update_status', methods=['POST'])
def update_status():
    app_id = request.form.get('id')
    new_status = request.form.get('status')

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE applications SET status=? WHERE id=?", (new_status, app_id))
        conn.commit()
        conn.close()
        flash("Status updated successfully!", "success")
    except Exception as e:
        print("Error updating status:", e)
        flash("Failed to update status.", "danger")

    return redirect('/admin')

# ---------------------------------------------------
# CLIENT — STATUS PAGE
# ---------------------------------------------------
@app.route("/status")
def status_page():
    return render_template("status.html")

# ---------------------------------------------------
# CLIENT — CHECK STATUS BY MOBILE
# ---------------------------------------------------
@app.route("/check_status", methods=["POST"])
def check_status():
    mobile = request.form.get("mobile")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, cert_type, status FROM applications WHERE mobile=?", (mobile,))
    result = c.fetchall()
    conn.close()

    return render_template("status.html", result=result, mobile=mobile)

# ---------------------------------------------------
# SERVE UPLOADED FILES
# ---------------------------------------------------
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ---------------------------------------------------
# RUN SERVER
# ---------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
