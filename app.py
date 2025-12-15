from flask import Flask, render_template, request, redirect, flash, session, jsonify
from supabase import create_client, Client
from werkzeug.utils import secure_filename
import os, time, uuid, requests
import razorpay

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

# ------------------- RAZORPAY CONFIG -------------------
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_Rrku9cNMfmMaVJ")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "7QKknj28ryZjcAP3ezkerqbI")
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# ------------------- FAST2SMS CONFIG -------------------
FAST2SMS_API_KEY = "YOUR_FAST2SMS_API_KEY"
ADMIN_MOBILE = "8847842809"

def send_sms(client_name, cert_type, mobile):
    url = "https://www.fast2sms.com/dev/bulkV2"
    message = f"New Application\nName: {client_name}\nCertificate: {cert_type}\nMobile: {mobile}"
    payload = {"route": "v3","message": message,"numbers": ADMIN_MOBILE,"language": "english"}
    headers = {"Authorization": FAST2SMS_API_KEY,"Content-Type": "application/json"}
    try:
        requests.post(url, json=payload, headers=headers)
    except:
        pass

# ------------------- FILE UPLOAD -------------------
def upload_to_supabase(file, folder):
    if not file or file.filename == "":
        return None
    filename = secure_filename(file.filename)
    unique = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    path = f"{folder}/{unique}-{filename}"
    try:
        supabase.storage.from_(BUCKET_NAME).upload(path, file.read(), {"content-type": file.content_type})
    except:
        return None
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{path}"

# ------------------- ADMIN CREDENTIALS -------------------
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
        "status": "Pending"
    }
    res = supabase.table("applications").insert(data).execute()
    app_id = res.data[0]["id"]
    send_sms(data["name"], data["cert_type"], data["mobile"])
    return redirect(f"/pay/{app_id}")

# ------------------- CREATE PAYMENT -------------------
@app.route("/pay/<int:app_id>")
def pay(app_id):
    order = razorpay_client.order.create({
        "amount": 200,  # ₹2
        "currency": "INR",
        "payment_capture": 1
    })
    supabase.table("applications").update({"razorpay_order_id": order["id"]}).eq("id", app_id).execute()
    return render_template("payment.html", order=order, razorpay_key=RAZORPAY_KEY_ID, app_id=app_id)

# ------------------- VERIFY PAYMENT -------------------
@app.route("/verify-payment", methods=["POST"])
def verify_payment():
    data = request.json
    try:
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": data["razorpay_order_id"],
            "razorpay_payment_id": data["razorpay_payment_id"],
            "razorpay_signature": data["razorpay_signature"]
        })
        supabase.table("applications").update({
            "payment_status": "Paid",
            "razorpay_payment_id": data["razorpay_payment_id"]
        }).eq("id", data["app_id"]).execute()
        return jsonify({"status": "success"})
    except:
        return jsonify({"status": "failed"}), 400

# ------------------- PAYMENT SUCCESS PAGE -------------------
@app.route("/payment-success/<int:app_id>")
def payment_success(app_id):
    data = supabase.table("applications").select("*").eq("id", app_id).execute().data
    if not data:
        return "Invalid Application"
    return render_template("payment_success.html", data=data[0])

# ------------------- DOWNLOADS -------------------
@app.route("/download/certificate/<int:app_id>")
def download_certificate(app_id):
    data = supabase.table("applications").select("*").eq("id", app_id).execute().data
    if not data:
        return "Invalid Request"
    app_data = data[0]
    if app_data["payment_status"] != "Paid":
        return "Payment required"
    if not app_data.get("certificate_file"):
        return "Certificate not uploaded"
    return redirect(app_data["certificate_file"])

@app.route("/download/receipt/<int:app_id>")
def download_receipt(app_id):
    data = supabase.table("applications").select("*").eq("id", app_id).execute().data
    if not data or data[0]["payment_status"] != "Paid":
        return "Payment required"
    return redirect(data[0]["receipt_file"])

# ------------------- ADMIN LOGIN -------------------
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("username") == ADMIN_USERNAME and request.form.get("password") == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect("/admin")
        flash("Invalid credentials", "login")
    return render_template("admin_login.html")

@app.route("/admin")
def admin():
    if not session.get("admin_logged_in"):
        return redirect("/admin-login")
    data = supabase.table("applications").select("*").order("id", desc=True).execute()
    return render_template("admin.html", applications=data.data)

@app.route("/admin-logout")
def admin_logout():
    session.clear()
    return redirect("/")

# ------------------- ADMIN ACTIONS -------------------
@app.route("/upload_certificate", methods=["POST"])
def upload_certificate():
    file = request.files.get("certificate")
    if file:
        url = upload_to_supabase(file, "certificate")
        supabase.table("applications").update({"certificate_file": url}).eq("id", request.form.get("id")).execute()
    return redirect("/admin")

@app.route("/upload_receipt", methods=["POST"])
def upload_receipt():
    file = request.files.get("receipt")
    if file:
        url = upload_to_supabase(file, "receipt")
        supabase.table("applications").update({"receipt_file": url}).eq("id", request.form.get("id")).execute()
    return redirect("/admin")

# ------------------- RUN APP -------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
