from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "something_super_secret"

# ------------------- FOLDER PATHS -------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

UPLOAD_FOLDER = os.path.join(STATIC_DIR, "uploads")
RECEIPT_FOLDER = os.path.join(STATIC_DIR, "receipts")
PAYMENT_FOLDER = os.path.join(STATIC_DIR, "payments")
QR_FILE = "static/your_qr.png"  # QR code image

# Safe folder creation
for folder in [UPLOAD_FOLDER, RECEIPT_FOLDER, PAYMENT_FOLDER]:
    if os.path.exists(folder):
        if not os.path.isdir(folder):
            os.remove(folder)
            os.makedirs(folder)
    else:
        os.makedirs(folder)

# ------------------- DATABASE -------------------
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
            mobile TEXT UNIQUE,
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
            receipt_file TEXT,
            certificate_file TEXT,
            status TEXT DEFAULT 'Pending',
            payment_status TEXT DEFAULT 'Pending'
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ------------------- ADMIN CREDENTIALS -------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "12345"

# ------------------- HELPER -------------------
def save_file(file, folder):
    if file and file.filename != "":
        filename = secure_filename(file.filename)
        path = os.path.join(folder, filename)
        file.save(path)
        return filename
    return None

# ------------------- ROUTES -------------------
@app.route("/")
def index():
    return render_template("index.html")

# ------------------- SUBMIT APPLICATION -------------------
@app.route("/submit", methods=["POST"])
def submit():
    cert_type = request.form.get("cert_type")
    name = request.form.get("name")
    mobile = request.form.get("mobile")
    village = request.form.get("village")
    post = request.form.get("post")
    gp = request.form.get("gp")
    pin = request.form.get("pin")
    district = request.form.get("district")
    state = request.form.get("state")

    # Use correct HTML 'name' attributes
    photo_file = save_file(request.files.get("photo"), UPLOAD_FOLDER)
    aadhaar_file = save_file(request.files.get("aadhaar"), UPLOAD_FOLDER)
    father_file = save_file(request.files.get("father_aadhaar"), UPLOAD_FOLDER)
    ror_file = save_file(request.files.get("ror"), UPLOAD_FOLDER)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO applications
        (cert_type, name, mobile, village, post, gp, pin, district, state,
         aadhar_file, ror_file, father_aadhar_file, applicant_photo)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (cert_type, name, mobile, village, post, gp, pin, district, state,
          aadhaar_file, ror_file, father_file, photo_file))
    conn.commit()
    conn.close()
    return redirect("/thanks")

@app.route("/thanks")
def thanks():
    return render_template("thanks.html")

# ------------------- ADMIN LOGIN -------------------
@app.route("/admin-login", methods=["GET","POST"])
def admin_login():
    if request.method=="POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username==ADMIN_USERNAME and password==ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect("/admin")
        else:
            flash("Invalid credentials!")
            return redirect("/admin-login")
    return render_template("admin_login.html")

# ------------------- ADMIN DASHBOARD -------------------
@app.route("/admin", methods=["GET","POST"])
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect("/admin-login")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Upload certificate or receipt
    if request.method=="POST":
        app_id = request.form.get("id")
        cert_file = request.files.get("certificate")
        receipt_file = request.files.get("receipt")

        if cert_file:
            filename = save_file(cert_file, RECEIPT_FOLDER)
            cur.execute("UPDATE applications SET certificate_file=? WHERE id=?", (filename, app_id))
        if receipt_file:
            filename = save_file(receipt_file, PAYMENT_FOLDER)
            cur.execute("UPDATE applications SET receipt_file=?, payment_status='Paid' WHERE id=?", (filename, app_id))

        conn.commit()
        flash("Files uploaded successfully!")

    cur.execute("SELECT * FROM applications ORDER BY id DESC")
    applications = cur.fetchall()
    conn.close()
    return render_template("admin.html", applications=applications)

# ------------------- LOGOUT -------------------
@app.route("/admin-logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect("/")

# ------------------- UPDATE STATUS -------------------
@app.route("/update_status", methods=["POST"])
def update_status():
    app_id = request.form.get("id")
    status = request.form.get("status")
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
    app_id = request.form.get("id")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT aadhar_file, ror_file, father_aadhar_file, applicant_photo, receipt_file, certificate_file FROM applications WHERE id=?", (app_id,))
    files = c.fetchone()
    paths = [UPLOAD_FOLDER, UPLOAD_FOLDER, UPLOAD_FOLDER, UPLOAD_FOLDER, PAYMENT_FOLDER, RECEIPT_FOLDER]
    for i, f in enumerate(files):
        if f:
            f_path = os.path.join(paths[i], f)
            if os.path.exists(f_path):
                os.remove(f_path)
    c.execute("DELETE FROM applications WHERE id=?", (app_id,))
    conn.commit()
    conn.close()
    flash("Application deleted!")
    return redirect("/admin")

# ------------------- CLIENT STATUS -------------------
@app.route("/status")
def status_page():
    return render_template("status.html")

@app.route("/check_status", methods=["POST"])
def check_status():
    mobile = request.form.get("mobile")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM applications WHERE mobile=?", (mobile,))
    app_data = cur.fetchone()
    conn.close()
    if app_data:
        return render_template("status.html", data=app_data, qr_file=QR_FILE)
    else:
        return render_template("status.html", message="No application found for this mobile number.")

# ------------------- DOWNLOAD FILES -------------------
@app.route("/downloads/receipt/<filename>")
def download_receipt(filename):
    return send_from_directory(PAYMENT_FOLDER, filename, as_attachment=True)

@app.route("/downloads/certificate/<filename>")
def download_certificate(filename):
    return send_from_directory(RECEIPT_FOLDER, filename, as_attachment=True)

# ------------------- RUN -------------------
if __name__=="__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port, debug=True)
