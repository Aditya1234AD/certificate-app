from flask import Flask, render_template, request, redirect, flash, session
from supabase import create_client, Client
from werkzeug.utils import secure_filename
import os
import time
import uuid
import requests

# ------------------- FLASK APP -------------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "local_dev_secret_key_1234567890")

# ------------------- SUPABASE CONFIG -------------------
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://souedaocajeetpmdixme.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv(
    "SUPABASE_SERVICE_KEY",
    "sb_secret_03LWwqFkrGo9Rus1U8SCzA_FMoatFbJ"
)
BUCKET_NAME = os.getenv("BUCKET_NAME", "uploads")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ------------------- FAST2SMS CONFIG -------------------
FAST2SMS_API_KEY = "Tc4HrYPZ25sl7MmAe8d3Ek1IRhiBzwNF0jCfpOQn9SqvoxUDWbFucA4ZapiGqtxK1rPOjy6LNfJgTDIk"
ADMIN_MOBILE = "8847842809"

# ------------------- SEND NORMAL SMS -------------------
def send_sms(client_name, cert_type, mobile):
    url = "https://www.fast2sms.com/dev/bulkV2"
    message = (
        f"New Application Received\n"
        f"Name: {client_name}\n"
        f"Certificate: {cert_type}\n"
        f"Client Mobile: {mobile}"
    )

    payload = {
        "route": "v3",
        "message": message,
        "numbers": ADMIN_MOBILE,
        "language": "english",
        "flash": 0
    }

    headers = {
        "Authorization": FAST2SMS_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        requests.post(url, json=payload, headers=headers)
    except Exception as e:
        print("SMS Error:", e)

# ------------------- FILE UPLOAD FUNCTION -------------------
def upload_to_supabase(file, folder_name):
    if not file or file.filename == "":
        return None

    original = secure_filename(file.filename)
    unique = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    filename = f"{unique}-{original}"
    path = f"{folder_name}/{filename}"

    try:
        supabase.storage.from_(BUCKET_NAME).upload(
            path,
            file.read(),
            {"content-type": file.content_type or "application/octet-stream"}
        )
    except Exception as e:
        print("Upload failed:", e)
        return None

    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{path}"

# ------------------- ADMIN LOGIN -------------------
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
    send_sms(data["name"], data["cert_type"], data["mobile"])

    flash("Application submitted successfully!", "client")
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
        flash("Invalid credentials!", "login")
        return redirect("/admin-login")
    return render_template("admin_login.html")

@app.route("/admin")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect("/admin-login")
    response = supabase.table("applications").select("*").order("id", desc=True).execute()
    return render_template("admin.html", applications=response.data)

@app.route("/admin-logout")
def admin_logout():
    session.clear()
    return redirect("/")

# ------------------- ADMIN ACTIONS -------------------
@app.route("/update_status", methods=["POST"])
def update_status():
    supabase.table("applications").update(
        {"status": request.form.get("status")}
    ).eq("id", request.form.get("id")).execute()

    flash("Status updated successfully!", "admin")
    return redirect("/admin")

@app.route("/delete_application", methods=["POST"])
def delete_application():
    supabase.table("applications").delete().eq(
        "id", request.form.get("id")
    ).execute()

    flash("Application deleted!", "admin")
    return redirect("/admin")

@app.route("/upload_certificate", methods=["POST"])
def upload_certificate():
    file = request.files.get("certificate")
    if file:
        url = upload_to_supabase(file, "certificate")
        supabase.table("applications").update(
            {"certificate_file": url}
        ).eq("id", request.form.get("id")).execute()
        flash("Certificate uploaded successfully!", "admin")
    else:
        flash("No file selected!", "admin")
    return redirect("/admin")

@app.route("/upload_receipt", methods=["POST"])
def upload_receipt():
    file = request.files.get("receipt")
    if file:
        url = upload_to_supabase(file, "receipt")
        supabase.table("applications").update(
            {"receipt_file": url, "payment_status": "Paid"}
        ).eq("id", request.form.get("id")).execute()
        flash("Receipt uploaded & payment marked Paid!", "admin")
    else:
        flash("No file selected!", "admin")
    return redirect("/admin")

# ------------------- CHECK STATUS -------------------
@app.route("/check-status", methods=["POST"])
def check_status():
    query = supabase.table("applications").select("*") \
        .eq("mobile", request.form.get("mobile")) \
        .eq("cert_type", request.form.get("cert_type")).execute()

    if query.data:
        return render_template("status.html", data=query.data[0])
    return render_template("status.html", message="No application found!")

# ------------------- LEGAL & PAYMENT PAGES -------------------
@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/razorpay")
def razorpay_policy():
    return render_template("razorpay.html")

# ------------------- RUN APP -------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
