from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "something_super_secret"  # Required for session management

# ------------------- FOLDERS -------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static/uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

RECEIPT_FOLDER = os.path.join(BASE_DIR, "static/receipts")
os.makedirs(RECEIPT_FOLDER, exist_ok=True)

PAYMENT_FOLDER = os.path.join(BASE_DIR, "static/payments")
os.makedirs(PAYMENT_FOLDER, exist_ok=True)

QR_FILE = os.path.join(BASE_DIR, "static/your_qr.png")  # Your payment QR

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["RECEIPT_FOLDER"] = RECEIPT_FOLDER
app.config["PAYMENT_FOLDER"] = PAYMENT_FOLDER

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
            status TEXT DEFAULT 'Pending',
            payment_ss TEXT,
            payment_status TEXT DEFAULT 'Pending',
            receipt_file TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ------------------- ADMIN CREDENTIALS -------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "12345"  # Change this

# ------------------- CLIENT PAGES -------------------
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

        def save_file(file, folder):
            if file and file.filename != "":
                path = os.path.join(folder, file.filename)
                file.save(path)
                return file.filename
            return None

        aadhar_file = save_file(aadhar, UPLOAD_FOLDER)
        father_aadhar_file = save_file(father_aadhar, UPLOAD_FOLDER)
        photo_file = save_file(applicant_photo, UPLOAD_FOLDER)
        ror_file = save_file(ror, UPLOAD_FOLDER)

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

# ------------------- CLIENT STATUS -------------------
@app.route("/status")
def status_page():
    return render_template("status.html")

@app.route("/check_status", methods=["POST"])
def check_status():
    mobile = request.form["mobile"]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, status, payment_status FROM applications WHERE mobile=?", (mobile,))
    result = c.fetchone()
    conn.close()
    if result:
        app_id, status, payment_status = result
        return render_template("status.html", status=status, payment_status=payment_status, app_id=app_id)
    else:
        return render_template("status.html", message="No application found for this mobile number.")

# ------------------- PAYMENT PAGE -------------------
@app.route("/receipt/<int:app_id>", methods=["GET", "POST"])
def receipt_page(app_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT payment_status, receipt_file FROM applications WHERE id=?", (app_id,))
    result = c.fetchone()
    conn.close()

    if not result:
        return "Application not found."

    payment_status, receipt_file = result

    if request.method == "POST":
        payment_file = request.files.get("payment_ss")
        if payment_file and payment_file.filename != "":
            filename = payment_file.filename
            path = os.path.join(PAYMENT_FOLDER, filename)
            payment_file.save(path)
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("UPDATE applications SET payment_ss=?, payment_status='Paid' WHERE id=?", (filename, app_id))
            conn.commit()
            conn.close()
            flash("Payment screenshot uploaded successfully!")
            return redirect(url_for("receipt_page", app_id=app_id))

    return render_template("receipt_download.html",
                           app_id=app_id,
                           payment_status=payment_status,
                           receipt_file=receipt_file,
                           qr_file="static/Screenshot_20251201_163839.JPG")

# ------------------- SERVE FILES -------------------
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/payments/<path:filename>")
def payment_file(filename):
    return send_from_directory(PAYMENT_FOLDER, filename)

@app.route("/receipts/<path:filename>")
def receipt_file(filename):
    return send_from_directory(RECEIPT_FOLDER, filename)

# ------------------- ADMIN -------------------
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid username or password!")
            return redirect(url_for("admin_login"))
    return render_template("admin_login.html")

@app.route("/admin")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
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
    return redirect(url_for("index"))

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

@app.route("/delete_application", methods=["POST"])
def delete_application():
    app_id = request.form["id"]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT aadhar_file, ror_file, father_aadhar_file, applicant_photo, receipt_file, payment_ss FROM applications WHERE id=?", (app_id,))
    files = c.fetchone()
    if files:
        for file in files:
            if file:
                for folder in [UPLOAD_FOLDER, RECEIPT_FOLDER, PAYMENT_FOLDER]:
                    path = os.path.join(folder, file)
                    if os.path.exists(path):
                        os.remove(path)
    c.execute("DELETE FROM applications WHERE id=?", (app_id,))
    conn.commit()
    conn.close()
    flash("Application and uploaded files deleted successfully!")
    return redirect("/admin")

# ------------------- RUN -------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
