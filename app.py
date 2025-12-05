from flask import Flask, render_template, request, redirect, flash, session
import sqlite3
from supabase import create_client, Client
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "something_super_secret"

# ------------------- SUPABASE CONFIG -------------------
SUPABASE_URL = "https://souedaocajeetpmdixme.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNvdWVkYW9jYWplZXRwbWRpeG1lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ4NTk2ODcsImV4cCI6MjA4MDQzNTY4N30.3QOeS3jpI6f1-auxKlYmUZCjZmJRqBomnINuy6xkn6Q"  # <-- Replace with your Service Role Key
BUCKET_NAME = "uploads"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ------------------- SUPABASE UPLOAD FUNCTION -------------------
def upload_to_supabase(file, folder_name):
    if file and file.filename != "":
        filename = secure_filename(file.filename)
        file_bytes = file.read()
        path_in_bucket = f"{folder_name}/{filename}"

        try:
            supabase.storage.from_(BUCKET_NAME).upload(
                path_in_bucket,
                file_bytes,
                {"content-type": file.content_type}
            )
        except Exception as e:
            print("Supabase upload failed:", e)
            return None

        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{folder_name}/{filename}"
        return public_url
    return None

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
            payment_status TEXT DEFAULT 'Pending'
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ------------------- ADMIN -------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "12345"

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

    # Upload files to Supabase
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
    """,(cert_type,name,mobile,village,post,gp,pin,district,state,
         aadhar_file, ror_file, father_file, photo_file))

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
        return render_template("status.html", message="No application found.")

# ------------------- UPLOAD PAYMENT -------------------
@app.route("/upload_payment/<int:app_id>", methods=["POST"])
def upload_payment(app_id):
    file = request.files.get("payment_ss")

    if file:
        file_url = upload_to_supabase(file, "payment")

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE applications SET payment_status='Paid', receipt_file=? WHERE id=?",
                    (file_url, app_id))
        conn.commit()
        conn.close()

        flash("Payment uploaded successfully!")

    return redirect("/status")

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

# ------------------- RUN -------------------
if __name__=="__main__":
    import os
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port, debug=True)
