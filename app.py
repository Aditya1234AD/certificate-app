from flask import Flask, render_template, request, redirect, url_for, flash
import os
import json

app = Flask(__name__)
app.secret_key = "mysecretkey"

UPLOAD_FOLDER = "uploads"
DATA_FILE = "data.json"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ------------------------ Save Data ------------------------
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ------------------------ Load Data ------------------------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "cert_type": "",
            "name": "",
            "mobile": "",
            "village": "",
            "post": "",
            "gp": "",
            "pin": "",
            "district": "",
            "state": "",
            "photo": "",
            "aadhaar": "",
            "father_aadhaar": "",
            "ror": "",
            "status": "Not Updated"
        }
    with open(DATA_FILE, "r") as f:
        return json.load(f)

# ------------------------ Index Page ------------------------
@app.route("/")
def index():
    return render_template("index.html")

# ------------------------ Submit Application ------------------------
@app.route("/submit", methods=["POST"])
def submit():
    data = load_data()

    # Get text fields
    data["cert_type"] = request.form.get("cert_type")
    data["name"] = request.form.get("name")
    data["mobile"] = request.form.get("mobile")
    data["village"] = request.form.get("village")
    data["post"] = request.form.get("post")
    data["gp"] = request.form.get("gp")
    data["pin"] = request.form.get("pin")
    data["district"] = request.form.get("district")
    data["state"] = request.form.get("state")

    # List of file fields
    file_fields = ["photo", "aadhaar", "father_aadhaar", "ror"]

    for field in file_fields:
        file = request.files.get(field)
        if file and file.filename != "":
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
            data[field] = file.filename

    save_data(data)
    return render_template("thanks.html")

# ------------------------ Admin Page ------------------------
@app.route("/admin")
def admin():
    data = load_data()
    return render_template("admin.html", data=data)

# ------------------------ Update Status ------------------------
@app.route("/update_status", methods=["POST"])
def update_status():
    data = load_data()
    status_text = request.form.get("status")
    data["status"] = status_text

    save_data(data)

    flash("Status Updated Successfully!")
    return redirect(url_for("admin"))

# ------------------------ Client Status Page ------------------------
@app.route("/status")
def status():
    data = load_data()
    return render_template("status.html", data=data)

# ------------------------ Render Deployment ------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
