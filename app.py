from flask import Flask, render_template, request, redirect, flash, session
import sqlite3
from supabase import create_client, Client
from werkzeug.utils import secure_filename
import os
import time
import uuid

# ------------------- FLASK APP -------------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "local_dev_secret_key_1234567890")

# ------------------- SUPABASE CONFIG -------------------
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://souedaocajeetpmdixme.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "<YOUR_SERVICE_KEY>")
BUCKET_NAME = os.getenv("BUCKET_NAME", "uploads")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ------------------- SUPABASE UPLOAD FUNCTION -------------------
def upload_to_supabase(file, folder_name):
    if not file or file.filename == "":
        return None
    original = secure_filename(file.filename)
    unique_suffix = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    filename = f"{unique_suffix}-{original}"
    path_in_bucket = f"{folder_name}/{filename}"

    try:
        file_bytes = file.read()
        supabase.storage.from_(BUCKET_NAME).upload(
            path_in_bucket,
            file_bytes,
            {"content-type": file.content_type or "application/octet-stream"}
        )
    except Exception as e:
        print("Supabase upload failed:", repr(e))
        return None

    try:
        result = supabase.storage.from_(BUCKET_NAME).get_public_url(path_in_bucket)
        public_url = result.get("publicUrl") or result.get("public_url")
        if public_url:
            return public_url
    except Exception as e:
        print("get_public_url failed:", repr(e))

    fallback = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{path_in_bucket}"
    return fallback

# ------------------- DATABASE -------------------
DB_PATH = "applications.db"

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
            payment_status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ------------------- ADMIN CREDENTIALS -------------------
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "12345")

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

    # Upload files
    aadhar_file = upload_to_supabase(request.files.get("aadhaar"), "aadhaar")
    father_file = upload_to_supabase(request.files.get("father_aadhaar"), "father_aadhaar")
    photo_file = upload_to_supabase(request.files.get("photo"), "photos")
    ror_file = upload_to_supabase(request.files.get("ror"), "ror")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO applications 
        (cert_type,name,mobile,village,post,gp,pin,district,state,
         aadhar_file,ror_file,father_aadhar_file,applicant_photo)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (cert_type, name, mobile, village, post, gp, pin, district, state,
          aadhar_file, ror_file, father_file, photo_file))
    conn.commit()
    conn.close()

    flash("Application submitted successfully!")
    return redirect("/thanks")

@app.route("/thanks")
def thanks():
    return render_template("thanks.html")

# ------------------- ADMIN LOGIN -------------------
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
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

# ------------------- UPDATE STATUS -------------------
@app.route("/update_status", methods=["POST"])
def update_status():
    app_id = request.form.get("id")
    status = request.form.get("status")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE applications SET status=? WHERE id=?", (status, app_id))
    conn.commit()
    conn.close()
    flash("Status updated successfully!")
    return redirect("/admin")

# ------------------- DELETE APPLICATION -------------------
@app.route("/delete_application", methods=["POST"])
def delete_application():
    app_id = request.form.get("id")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM applications WHERE id=?", (app_id,))
    conn.commit()
    conn.close()
    flash("Application deleted!")
    return redirect("/admin")

# ------------------- UPLOAD CERTIFICATE -------------------
@app.route("/upload_certificate", methods=["POST"])
def upload_certificate():
    app_id = request.form.get("id")
    file = request.files.get("certificate")

    if file:
        file_url = upload_to_supabase(file, "certificate")
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE applications SET certificate_file=? WHERE id=?", (file_url, app_id))
        conn.commit()
        conn.close()
        flash("Certificate uploaded successfully!")
    else:
        flash("No file selected!")
    return redirect("/admin")

# ------------------- RUN APP -------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
