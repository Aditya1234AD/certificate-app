from flask import Flask, render_template, request, redirect, flash, session, url_for
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
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "sb_secret_03LWwqFkrGo9Rus1U8SCzA_FMoatFbJ")
BUCKET_NAME = os.getenv("BUCKET_NAME", "uploads")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ------------------- FILE UPLOAD FUNCTION -------------------
def upload_to_supabase(file, folder_name):
    if not file or file.filename == "":
        return None

    original = secure_filename(file.filename)
    unique_suffix = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    filename = f"{unique_suffix}-{original}"
    path = f"{folder_name}/{filename}"

    try:
        file_bytes = file.read()
        supabase.storage.from_(BUCKET_NAME).upload(
            path,
            file_bytes,
            {"content-type": file.content_type or "application/octet-stream"},
        )
    except Exception as e:
        print("Upload failed:", e)
        return None

    try:
        url_obj = supabase.storage.from_(BUCKET_NAME).get_public_url(path)
        public_url = url_obj.get("publicUrl") or url_obj.get("public_url")
        if public_url:
            return public_url
    except Exception:
        pass

    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{path}"

# ------------------- ADMIN LOGIN CREDENTIALS -------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "12345"

# ------------------- ROUTES -------------------
@app.route("/")
def index():
    return render_template("index.html")

# ------------------- SUBMIT APPLICATION -------------------
@app.route("/submit", methods=["POST"])
def submit():
    data = {
        "cert_type": request.form.get("cert_type"),
        "name": request.form.get("name"),
        "mobile": request.form.get("mobile"),
        "village": request.form.get("village"),
        "post": request.form.get("post"),
        "gp": request.form.get("gp"),
        "pin": request.form.get("pin"),
        "district": request.form.get("district"),
        "state": request.form.get("state"),
        "aadhar_file": upload_to_supabase(request.files.get("aadhaar"), "aadhaar"),
        "father_aadhar_file": upload_to_supabase(request.files.get("father_aadhaar"), "father_aadhaar"),
        "applicant_photo": upload_to_supabase(request.files.get("photo"), "photos"),
        "ror_file": upload_to_supabase(request.files.get("ror"), "ror"),
        "payment_status": "Pending",
        "status": "Pending",
    }

    supabase.table("applications").insert(data).execute()
    flash("Application submitted successfully!")
    return redirect("/thanks")

@app.route("/thanks")
def thanks():
    return render_template("thanks.html")

# ------------------- ADMIN LOGIN -------------------
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("username") == ADMIN_USERNAME and request.form.get("password") == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect("/admin")

        flash("Invalid credentials!")
        return redirect("/admin-login")

    return render_template("admin_login.html")

@app.route("/admin")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect("/admin-login")

    response = supabase.table("applications").select("*").order("id", desc=True).execute()
    applications = response.data

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
    supabase.table("applications").update({"status": status}).eq("id", app_id).execute()
    flash("Status updated successfully!")
    return redirect("/admin")

# ------------------- DELETE APPLICATION -------------------
@app.route("/delete_application", methods=["POST"])
def delete_application():
    app_id = request.form.get("id")
    supabase.table("applications").delete().eq("id", app_id).execute()
    flash("Application deleted!")
    return redirect("/admin")

# ------------------- UPLOAD CERTIFICATE -------------------
@app.route("/upload_certificate", methods=["POST"])
def upload_certificate():
    app_id = request.form.get("id")
    file = request.files.get("certificate")

    if file:
        url = upload_to_supabase(file, "certificate")
        supabase.table("applications").update({"certificate_file": url}).eq("id", app_id).execute()
        flash("Certificate uploaded successfully!")
    else:
        flash("No file selected!")

    return redirect("/admin")

# ------------------- UPLOAD RECEIPT -------------------
@app.route("/upload_receipt", methods=["POST"])
def upload_receipt():
    app_id = request.form.get("id")
    file = request.files.get("receipt")

    if file:
        url = upload_to_supabase(file, "receipt")
        supabase.table("applications").update({
            "receipt_file": url,
            "payment_status": "Paid"
        }).eq("id", app_id).execute()
        flash("Receipt uploaded and payment marked as Paid!")
    else:
        flash("No file selected!")

    return redirect("/admin")

# ------------------- CHECK STATUS -------------------
@app.route("/check-status", methods=["POST"])
def check_status():
    mobile = request.form.get("mobile")
    cert_type = request.form.get("cert_type")

    query = (
        supabase.table("applications")
        .select("*")
        .eq("mobile", mobile)
        .eq("cert_type", cert_type)
        .execute()
    )

    if query.data:
        return render_template("status.html", data=query.data[0])
    else:
        return render_template("status.html", message="No application found!")

# ------------------- RUN APP -------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
