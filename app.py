from flask import Flask, render_template, request, redirect, send_from_directory
import os
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)

# FOLDER STRUCTURE
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
RECEIPT_FOLDER = os.path.join(BASE_DIR, "static", "receipts")
CERTIFICATE_FOLDER = os.path.join(BASE_DIR, "static", "certificates")

# Create folders ONLY IF NOT EXISTS
for path in [UPLOAD_FOLDER, RECEIPT_FOLDER, CERTIFICATE_FOLDER]:
    if not os.path.exists(path):
        os.makedirs(path)

DATA_FILE = "data.json"


# ------------------------------------------------------------------------------
# LOAD & SAVE JSON DATABASE
# ------------------------------------------------------------------------------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ------------------------------------------------------------------------------
# HOME PAGE (Client Upload Form)
# ------------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ------------------------------------------------------------------------------
# CLIENT SUBMISSION
# ------------------------------------------------------------------------------
@app.route("/submit", methods=["POST"])
def submit():
    mobile = request.form["mobile"]
    name = request.form["name"]

    # MAIN DOCUMENT UPLOAD
    file = request.files["document"]
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # STORE IN DATABASE
    data = load_data()
    data[mobile] = {
        "name": name,
        "document": filename,
        "status": "Submitted",
        "payment_status": "Pending",
        "receipt_file": "",
        "certificate_file": ""
    }
    save_data(data)

    return redirect("/thanks")


@app.route("/thanks")
def thanks():
    return render_template("thanks.html")


# ------------------------------------------------------------------------------
# STATUS CHECK PAGE
# ------------------------------------------------------------------------------
@app.route("/check_status", methods=["POST"])
def check_status():
    mobile = request.form["mobile"]
    data = load_data()

    if mobile not in data:
        return render_template("status.html", message="No record found.")

    return render_template("status.html", data=data[mobile])


# ------------------------------------------------------------------------------
# ADMIN PANEL
# ------------------------------------------------------------------------------
@app.route("/admin")
def admin():
    data = load_data()
    return render_template("admin.html", applications=data)


# ------------------------------------------------------------------------------
# ADMIN UPDATE APPLICATION
# ------------------------------------------------------------------------------
@app.route("/update/<mobile>", methods=["POST"])
def update(mobile):
    data = load_data()

    if mobile not in data:
        return "Mobile number not found"

    # Update status
    data[mobile]["status"] = request.form["status"]
    data[mobile]["payment_status"] = request.form["payment_status"]

    # Upload RECEIPT (Admin uploads only)
    if "receipt" in request.files:
        r = request.files["receipt"]
        if r.filename:
            rname = secure_filename(r.filename)
            r.save(os.path.join(RECEIPT_FOLDER, rname))
            data[mobile]["receipt_file"] = rname

    # Upload CERTIFICATE (Admin uploads only)
    if "certificate" in request.files:
        c = request.files["certificate"]
        if c.filename:
            cname = secure_filename(c.filename)
            c.save(os.path.join(CERTIFICATE_FOLDER, cname))
            data[mobile]["certificate_file"] = cname

    save_data(data)
    return redirect("/admin")


# ------------------------------------------------------------------------------
# FILE DOWNLOAD ROUTES
# ------------------------------------------------------------------------------
@app.route("/download/receipt/<filename>")
def download_receipt(filename):
    return send_from_directory(RECEIPT_FOLDER, filename, as_attachment=True)

@app.route("/download/certificate/<filename>")
def download_certificate(filename):
    return send_from_directory(CERTIFICATE_FOLDER, filename, as_attachment=True)


# ------------------------------------------------------------------------------
# RUN
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use Render's assigned port
    app.run(host="0.0.0.0", port=port, debug=True)
