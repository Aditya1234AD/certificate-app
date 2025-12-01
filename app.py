from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "something_super_secret"

# ------------------- FOLDER PATHS -------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

UPLOAD_FOLDER = os.path.join(STATIC_DIR, "uploads")        # Client documents
RECEIPT_FOLDER = os.path.join(STATIC_DIR, "receipts")      # Admin uploaded receipt
CERT_FOLDER = os.path.join(STATIC_DIR, "certificates")     # Admin uploaded certificate
PAYMENT_FOLDER = os.path.join(STATIC_DIR, "payments")      # Client uploaded payment screenshot

QR_FILE = "/static/qr.png"   # Put qr.png in static/ folder

# Safe folder creation
for folder in [UPLOAD_FOLDER, RECEIPT_FOLDER, CERT_FOLDER, PAYMENT_FOLDER]:
    os.makedirs(folder, exist_ok=True)

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

            receipt_file TEXT,         -- admin uploaded receipt
            certificate_file TEXT,     -- admin uploaded certificate

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
def submit_form():
    cert_type = request.form.get("cert_type")
    name = request.form.get("name")
    mobile = request.form.get("mobile")
    village = request.form.get("village")
    post = request.form.get("post")
    gp = request.form.get("gp")
    pin = request.form.get("pin")
    district = request.form.get("district")
    state = request.form.get("state")

    aadhar_file = save_file(request.files.get("aadhaar"), UPLOAD_FOLDER)
    father_file = save_file(request.files.get("father_aadhaar"), UPLOAD_FOLDER)
    photo_file = save_file(request.files.get("photo"), UPLOAD_FOLDER)
    ror_file = save_file(request.files.get("ror"), UPLOAD_FOLDER)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO applications
        (cert_type,name,mobile,village,post,gp,pin,district,state,
        aadhar_file,ror_file,father_aadhar_file,applicant_photo)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (cert_type,name,mobile,village,post,gp,pin,district,state,
          aadhar_file,ror_file,father_file,photo_file))
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
        if request.form.get("username")==ADMIN_USERNAME and request.form.get("password")==ADMIN_PASSWORD:
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

    # Admin uploading receipt + certificate
    if request.method == "POST":
        app_id = request.form.get("id")

        receipt = request.files.get("receipt")
        certificate = request.files.get("certificate")

        if receipt:
            rname = save_file(receipt, RECEIPT_FOLDER)
            cur.execute("UPDATE applications SET receipt_file=? WHERE id=?", (rname, app_id))

        if certificate:
            cname = save_file(certificate, CERT_FOLDER)
            cur.execute("UPDATE applications SET certificate_file=? WHERE id=?", (cname, app_id))

        conn.commit()
        flash("Files uploaded successfully!")

    cur.execute("SELECT * FROM applications ORDER BY id DESC")
    applications = cur.fetchall()
    conn.close()
    return render_template("admin.html", applications=applications)

# ------------------- UPDATE STATUS -------------------
@app.route("/update_status", methods=["POST"])
def update_status():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE applications SET status=? WHERE id=?", 
                (request.form.get("status"), request.form.get("id")))
    conn.commit()
    conn.close()
    flash("Status updated!")
    return redirect("/admin")

# ------------------- DELETE APPLICATION -------------------
@app.route("/delete_application", methods=["POST"])
def delete_application():
    app_id = request.form.get("id")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT aadhar_file, ror_file, father_aadhar_file, applicant_photo, receipt_file, certificate_file FROM applications WHERE id=?", (app_id,))
    files = cur.fetchone()

    # Delete files safely
    folders = [UPLOAD_FOLDER, UPLOAD_FOLDER, UPLOAD_FOLDER, UPLOAD_FOLDER, RECEIPT_FOLDER, CERT_FOLDER]
    for f, folder in zip(files, folders):
        if f:
            fpath = os.path.join(folder, f)
            if os.path.exists(fpath):
                os.remove(fpath)

    cur.execute("DELETE FROM applications WHERE id=?", (app_id,))
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

    return render_template("status.html", app=app_data, qr=QR_FILE)

# ------------------- PAYMENT UPLOAD -------------------
@app.route("/upload_payment/<int:app_id>", methods=["POST"])
def upload_payment(app_id):
    file = request.files.get("payment_ss")
    filename = save_file(file, PAYMENT_FOLDER)

    if filename:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE applications SET payment_status='Completed' WHERE id=?", (app_id,))
        conn.commit()
        conn.close()
        flash("Payment verified! You can now download files.")
    return redirect("/status")

# ------------------- FILE DOWNLOADS -------------------
@app.route("/certificate/<filename>")
def certificate_file(filename):
    return send_from_directory(CERT_FOLDER, filename)

@app.route("/receipt/<filename>")
def receipt_file(filename):
    return send_from_directory(RECEIPT_FOLDER, filename)

# ------------------- RUN -------------------
if __name__=="__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port, debug=True)
