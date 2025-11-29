from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "something_super_secret"

# ------------------- UPLOAD FOLDER -------------------
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")

# If 'uploads' exists as a file, delete it first
if os.path.exists(UPLOAD_FOLDER) and not os.path.isdir(UPLOAD_FOLDER):
    os.remove(UPLOAD_FOLDER)

# Create uploads folder safely
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ------------------- DATABASE -------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "applications.db")

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
            status TEXT DEFAULT 'Pending'
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ------------------- CLIENT PAGE -------------------
@app.route("/")
def index():
    return render_template("index.html")

# ------------------- FORM SUBMISSION -------------------
@app.route("/submit", methods=["POST"])
def submit_form():
    try:
        # Text inputs
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

        # Save files
        def save_file(file):
            if file and file.filename != "":
                filename = file.filename
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)
                return filename
            return None

        aadhar_file = save_file(aadhar)
        father_aadhar_file = save_file(father_aadhar)
        photo_file = save_file(applicant_photo)
        ror_file = save_file(ror)

        # Insert into DB
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO applications
            (cert_type, name, mobile, village, post, gp, pin, district, state,
            aadhar_file, ror_file, father_aadhar_file, applicant_photo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (cert_type, name, mobile, village, post, gp, pin, district, state,
              aadhar_file, ror_file, father_aadhar_file, photo_file))
        conn.commit()
        conn.close()

        return redirect("/thanks")

    except Exception as e:
        print("Error submitting application:", e)
        return f"Error submitting application: {e}"

# ------------------- THANK YOU PAGE -------------------
@app.route("/thanks")
def thanks():
    return render_template("thanks.html")

# ------------------- ADMIN PAGE -------------------
@app.route("/admin")
def admin():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM applications ORDER BY id DESC")  # fetch all applications
    applications = cur.fetchall()
    conn.close()
    return render_template("admin.html", applications=applications)

# ------------------- UPDATE STATUS -------------------
@app.route("/update_status", methods=["POST"])
def update_status():
    app_id = request.form["id"]
    status = request.form["status"]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE applications SET status=? WHERE id=?", (status, app_id))
    conn.commit()
    conn.close()
    flash("Status updated successfully!")
    return redirect("/admin")

# ------------------- DELETE APPLICATION -------------------
@app.route("/delete_application", methods=["POST"])
def delete_application():
    app_id = request.form["id"]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT aadhar_file, ror_file, father_aadhar_file, applicant_photo FROM applications WHERE id=?", (app_id,))
    files = c.fetchone()

    if files:
        for file in files:
            if file:
                file_path = os.path.join(UPLOAD_FOLDER, file)
                if os.path.exists(file_path):
                    os.remove(file_path)

    c.execute("DELETE FROM applications WHERE id=?", (app_id,))
    conn.commit()
    conn.close()
    flash("Application and uploaded files deleted successfully!")
    return redirect("/admin")

# ------------------- CLIENT STATUS PAGE -------------------
@app.route("/status")
def status_page():
    return render_template("status.html")

@app.route("/check_status", methods=["POST"])
def check_status():
    mobile = request.form["mobile"]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT status FROM applications WHERE mobile=?", (mobile,))
    result = c.fetchone()
    conn.close()
    if result:
        status = result[0] or "Pending"
        return render_template("status.html", status=status)
    else:
        return render_template("status.html", message="No application found for this mobile number.")

# ------------------- SERVE UPLOADED FILES -------------------
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ------------------- RUN APP -------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
