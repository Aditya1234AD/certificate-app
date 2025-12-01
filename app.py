from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "something_super_secret"

# ------------------- FOLDERS -------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_FOLDER = os.path.join(STATIC_DIR, "uploads")
RECEIPT_FOLDER = os.path.join(STATIC_DIR, "receipts")
PAYMENT_FOLDER = os.path.join(STATIC_DIR, "payments")

for folder in [UPLOAD_FOLDER, RECEIPT_FOLDER, PAYMENT_FOLDER]:
    if os.path.exists(folder):
        if not os.path.isdir(folder):
            os.remove(folder)
            os.makedirs(folder)
    else:
        os.makedirs(folder)

# ------------------- DATABASE -------------------
DB_PATH = os.path.join(BASE_DIR, "applications.db")

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
            receipt_file TEXT,
            certificate_file TEXT,
            status TEXT DEFAULT 'Pending',
            payment_status TEXT DEFAULT 'Pending'
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ------------------- ADMIN -------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "12345"

# ------------------- HELPERS -------------------
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
    flash("Application submitted successfully!")
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

@app.route("/admin")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect("/admin-login")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM applications ORDER BY id DESC")
    applications = cur.fetchall()
    conn.close()
    return render_template("admin.html", applications=applications)

@app.route("/admin-logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect("/")

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

@app.route("/delete_application", methods=["POST"])
def delete_application():
    app_id = request.form.get("id")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT aadhar_file, ror_file, father_aadhar_file, applicant_photo, certificate_file, receipt_file FROM applications WHERE id=?", (app_id,))
    files = c.fetchone()
    for idx, f in enumerate(files):
        if f:
            folder = UPLOAD_FOLDER if idx<4 else RECEIPT_FOLDER
            f_path = os.path.join(folder, f)
            if os.path.exists(f_path):
                os.remove(f_path)
    c.execute("DELETE FROM applications WHERE id=?", (app_id,))
    conn.commit()
    conn.close()
    flash("Application deleted!")
    return redirect("/admin")

# ------------------- CHECK STATUS -------------------
@app.route("/status")
def status_page():
    return render_template("status.html")

@app.route("/check_status", methods=["POST"])
def check_status():
    mobile = request.form.get("mobile")
    cert_type = request.form.get("cert_type")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM applications WHERE mobile=? AND cert_type=?", (mobile, cert_type))
    app_data = cur.fetchone()
    conn.close()
    if app_data:
        return render_template("status.html", data=app_data)
    else:
        return render_template("status.html", message="No application found for this mobile number and certificate type.")

# ------------------- UPLOAD PAYMENT -------------------
@app.route("/upload_payment/<int:app_id>", methods=["POST"])
def upload_payment(app_id):
    file = request.files.get("payment_ss")
    if file:
        filename = save_file(file, PAYMENT_FOLDER)
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE applications SET payment_status='Paid', receipt_file=? WHERE id=?", (filename, app_id))
        conn.commit()
        conn.close()
        flash("Payment completed successfully!")
    return redirect("/status")
    
    # ------------------- UPLOAD CERTIFICATE -------------------
@app.route("/upload_certificate", methods=["POST"])
def upload_certificate():
    app_id = request.form.get("id")
    file = request.files.get("certificate")
    if file:
        filename = save_file(file, RECEIPT_FOLDER)  # Save in receipts folder
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE applications SET certificate_file=? WHERE id=?", (filename, app_id))
        conn.commit()
        conn.close()
        flash("Certificate uploaded successfully!")
    else:
        flash("No file selected!")
    return redirect("/admin")

# ------------------- DOWNLOAD FILES -------------------
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/receipts/<path:filename>")
def download_receipt(filename):
    return send_from_directory(RECEIPT_FOLDER, filename, as_attachment=True)

@app.route("/certificate/<path:filename>")
def download_certificate(filename):
    return send_from_directory(RECEIPT_FOLDER, filename, as_attachment=True)

# ------------------- RUN -------------------
if __name__=="__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port, debug=True)
