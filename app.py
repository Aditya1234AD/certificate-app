from flask import Flask, render_template, request, redirect, flash, session, jsonify
from supabase import create_client, Client
from werkzeug.utils import secure_filename
import os, time, uuid, requests
import razorpay

# ------------------- FLASK APP -------------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "local_dev_secret_key_1234567890")

# ------------------- SUPABASE CONFIG -------------------
SUPABASE_URL = "https://souedaocajeetpmdixme.supabase.co"
SUPABASE_SERVICE_KEY = "sb_secret_03LWwqFkrGo9Rus1U8SCzA_FMoatFbJ"
BUCKET_NAME = "uploads"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ------------------- RAZORPAY CONFIG -------------------
RAZORPAY_KEY_ID = "rzp_test_Rrku9cNMfmMaVJ"
RAZORPAY_KEY_SECRET = "7QKknj28ryZjcAP3ezkerqbI"
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# ------------------- FILE UPLOAD FUNCTION -------------------
def upload_to_supabase(file, folder):
    if not file or file.filename == "":
        return None

    filename = secure_filename(file.filename)
    unique_name = f"{int(time.time())}-{uuid.uuid4().hex[:6]}-{filename}"
    path = f"{folder}/{unique_name}"

    supabase.storage.from_(BUCKET_NAME).upload(
        path,
        file.read(),
        {"content-type": file.content_type}
    )

    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{path}"

# ------------------- HOME -------------------
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

        "status": "Pending",
        "payment_status": "Pending",
        "payment_required": False
    }

    result = supabase.table("applications").insert(data).execute()
    app_id = result.data[0]["id"]

    return redirect(f"/check-status?app_id={app_id}")

# ------------------- CREATE PAYMENT -------------------
@app.route("/pay/<int:app_id>")
def pay(app_id):
    app_data = supabase.table("applications").select("*").eq("id", app_id).execute().data[0]

    # 🔒 SAFETY CHECK
    if not app_data["payment_required"] or app_data["payment_status"] == "Paid":
        return "Payment not allowed"

    order = razorpay_client.order.create({
        "amount": 20000,  # ₹200 (in paise)
        "currency": "INR",
        "payment_capture": 1
    })

    supabase.table("applications").update({
        "razorpay_order_id": order["id"]
    }).eq("id", app_id).execute()

    return render_template(
        "payment.html",
        order=order,
        razorpay_key=RAZORPAY_KEY_ID,
        app_id=app_id
    )

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
            "payment_required": False,
            "razorpay_payment_id": data["razorpay_payment_id"]
        }).eq("id", data["app_id"]).execute()

        return jsonify({"status": "success"})

    except:
        return jsonify({"status": "failed"}), 400

# ------------------- CHECK STATUS -------------------
@app.route("/check-status", methods=["GET", "POST"])
def check_status():
    if request.method == "POST":
        mobile = request.form.get("mobile")
        cert_type = request.form.get("cert_type")

        data = supabase.table("applications") \
            .select("*") \
            .eq("mobile", mobile) \
            .eq("cert_type", cert_type) \
            .order("id", desc=True) \
            .execute()

        if data.data:
            return render_template("status.html", data=data.data[0])

        return render_template("status.html", message="No application found")

    return render_template("check_status.html")
    # ------------------- UPDATE STATUS -------------------
@app.route("/update_status", methods=["POST"])
def update_status():
    if not session.get("admin_logged_in"):
        return redirect("/admin-login")

    app_id = request.form.get("id")
    status = request.form.get("status")

    if app_id and status:
        update_data = {"status": status}
        # Enable payment only if status is Processed or Approved
        if status in ["Processed", "Approved"]:
            update_data["payment_required"] = True
        supabase.table("applications").update(update_data).eq("id", app_id).execute()

    return redirect("/admin


# ------------------- DOWNLOADS -------------------
@app.route("/download/receipt/<int:app_id>")
def download_receipt(app_id):
    app_data = supabase.table("applications").select("*").eq("id", app_id).execute().data[0]

    if app_data["payment_status"] != "Paid":
        return "Payment required"

    if not app_data["receipt_file"]:
        return "Receipt not uploaded"

    return redirect(app_data["receipt_file"])

@app.route("/download/certificate/<int:app_id>")
def download_certificate(app_id):
    app_data = supabase.table("applications").select("*").eq("id", app_id).execute().data[0]

    if app_data["payment_status"] != "Paid":
        return "Payment required"

    if not app_data["certificate_file"]:
        return "Certificate not uploaded"

    return redirect(app_data["certificate_file"])

# ------------------- ADMIN LOGIN -------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "12345"

@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("username") == ADMIN_USERNAME and request.form.get("password") == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect("/admin")
        flash("Invalid login")

    return render_template("admin_login.html")

@app.route("/admin")
def admin():
    if not session.get("admin_logged_in"):
        return redirect("/admin-login")

    apps = supabase.table("applications").select("*").order("id", desc=True).execute()
    return render_template("admin.html", applications=apps.data)

# ------------------- ADMIN ACTIONS -------------------
@app.route("/upload_receipt", methods=["POST"])
def upload_receipt():
    file = request.files.get("receipt")
    app_id = request.form.get("id")

    if file:
        url = upload_to_supabase(file, "receipt")
        supabase.table("applications").update({
            "receipt_file": url,
            "status": "Processed",
            "payment_required": True
        }).eq("id", app_id).execute()

    return redirect("/admin")

@app.route("/upload_certificate", methods=["POST"])
def upload_certificate():
    file = request.files.get("certificate")
    app_id = request.form.get("id")

    if file:
        url = upload_to_supabase(file, "certificate")
        supabase.table("applications").update({
            "certificate_file": url,
            "status": "Approved",
            "payment_required": True
        }).eq("id", app_id).execute()

    return redirect("/admin")
    # ------------------- STATIC PAGES -------------------
@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/payment-policy")
def payment_policy():
    return render_template("payment_policy.html")

# ------------------- LOGOUT -------------------
@app.route("/admin-logout")
def admin_logout():
    session.clear()
    return redirect("/")

# ------------------- RUN -------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
