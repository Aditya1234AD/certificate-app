from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "something_super_secret"

# ------------------- FOLDERS -------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static/uploads")
RECEIPT_FOLDER = os.path.join(BASE_DIR, "static/receipts")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RECEIPT_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["RECEIPT_FOLDER"] = RECEIPT_FOLDER

# QR code image path (static folder)
QR_FILE = "static/Screenshot_20251201_163839.JPG"

# ------------------- DATABASE -------------------
DB_PATH = os.path.join(BASE_DIR, "data/applications.db")
os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)

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
            status TEXT DEFAULT 'Pending',
            certificate_file TEXT,
            payment_status TEXT DEFAULT 'Pending'
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ------------------- ADMIN CREDENTIALS -------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "12345"

# ------------------- CLIENT PAGE -------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit_form():
    try:
        cert_type = request.form.get("cert_type")
        name = request.form.get("name")
        mobile = request.form.get("mobile")
        village = request.form.get("village")
        post = request.form.get("post")
        gp = request.form.get("gp")
        pin = request.form.get("pin")
        district = request.form.get("district")
        state = request.form.get("state")

        aadhar = request.files.get("aadhaar")
        father_aadhar = request.files.get("father_aadhaar")
        applicant_photo = request.files.get("photo")
        ror = request.files.get("ror")  

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

@app.route("/admin-logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect("/")

# ------------------- ADMIN DASHBOARD -------------------
@app.route("/admin", methods=["GET","POST"])
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect("/admin-login")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Upload certificate by admin
    if request.method=="POST":
        app_id = request.form["id"]
        cert_file = request.files.get("certificate")
        if cert_file and cert_file.filename != "":
            filename = f"certificate_{app_id}_{cert_file.filename}"
            cert_file.save(os.path.join(RECEIPT_FOLDER, filename))
            cur.execute("UPDATE applications SET certificate_file=? WHERE id=?", (filename, app_id))
            conn.commit()
            flash("Certificate uploaded successfully!")

    cur.execute("SELECT * FROM applications ORDER BY id DESC")
    applications = cur.fetchall()
    conn.close()
    return render_template("admin.html", applications=applications)

# ------------------- STATUS PAGE -------------------
@app.route("/status")
def status_page():
    return render_template("status.html")

@app.route("/check_status", methods=["POST"])
def check_status():
    mobile = request.form["mobile"]
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM applications WHERE mobile=?", (mobile,))
    application = cur.fetchone()
    conn.close()
    if application:
        return render_template("status.html", application=application, qr_file=QR_FILE)
    else:
        return render_template("status.html", message="No application found for this mobile number.")

# ------------------- PAYMENT SCREENSHOT UPLOAD -------------------
@app.route("/upload_payment/<int:app_id>", methods=["POST"])
def upload_payment(app_id):
    payment_file = request.files.get("payment_ss")
    if payment_file and payment_file.filename != "":
        filename = f"payment_{app_id}_{payment_file.filename}"
        payment_file.save(os.path.join(RECEIPT_FOLDER, filename))
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE applications SET payment_status='Completed' WHERE id=?", (app_id,))
        conn.commit()
        conn.close()
        flash("Payment confirmed! Certificate ready to download.")
    return redirect("/status")

# ------------------- SERVE FILES -------------------
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/receipts/<path:filename>")
def serve_receipt(filename):
    return send_from_directory(RECEIPT_FOLDER, filename)

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
    c.execute("SELECT aadhar_file, ror_file, father_aadhar_file, applicant_photo, certificate_file FROM applications WHERE id=?", (app_id,))
    files = c.fetchone()
    if files:
        for file in files:
            if file:
                file_path = os.path.join(UPLOAD_FOLDER if file!=files[4] else RECEIPT_FOLDER, file)
                if os.path.exists(file_path):
                    os.remove(file_path)
    c.execute("DELETE FROM applications WHERE id=?", (app_id,))
    conn.commit()
    conn.close()
    flash("Application and files deleted successfully!")
    return redirect("/admin")

# ------------------- RUN APP -------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
