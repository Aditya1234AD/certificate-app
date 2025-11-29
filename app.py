from flask import Flask, render_template, request, redirect, send_from_directory, flash
import os
import json

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------------------------------------------
# DIRECTORIES
# ---------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = "/tmp/uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

DB_PATH = os.path.join(BASE_DIR, "applications.json")
if not os.path.exists(DB_PATH):
    with open(DB_PATH, "w") as f:
        json.dump([], f)

# ---------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------
def load_data():
    with open(DB_PATH, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=4)

# ---------------------------------------------------
# ROUTES
# ---------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/submit", methods=["POST"])
def submit_form():
    try:
        # Text Inputs
        cert_type = request.form.get("cert_type")
        name = request.form.get("name")
        mobile = request.form.get("mobile")
        village = request.form.get("village")
        post = request.form.get("post")
        gp = request.form.get("gp")
        pin = request.form.get("pin")
        district = request.form.get("district")
        state = request.form.get("state")

        # Files
        aadhar = request.files.get("aadhaar")
        father_aadhar = request.files.get("father_aadhaar")
        applicant_photo = request.files.get("photo")
        ror = request.files.get("ror")  # optional

        # Required file checks
        if not aadhar or aadhar.filename == "":
            return "Applicant Aadhaar is required.", 400
        if not father_aadhar or father_aadhar.filename == "":
            return "Father Aadhaar is required.", 400
        if not applicant_photo or applicant_photo.filename == "":
            return "Applicant photo is required.", 400

        # File names — use basename to avoid path issues
        aadhar_filename = os.path.basename(aadhar.filename)
        father_filename = os.path.basename(father_aadhar.filename)
        photo_filename = os.path.basename(applicant_photo.filename)
        ror_filename = os.path.basename(ror.filename) if ror and ror.filename != "" else None

        # Save files
        aadhar.save(os.path.join(UPLOAD_FOLDER, aadhar_filename))
        father_aadhar.save(os.path.join(UPLOAD_FOLDER, father_filename))
        applicant_photo.save(os.path.join(UPLOAD_FOLDER, photo_filename))
        if ror_filename:
            ror.save(os.path.join(UPLOAD_FOLDER, ror_filename))

        # Load existing applications
        data = load_data()
        new_id = len(data) + 1

        # Save application
        application = {
            "id": new_id,
            "cert_type": cert_type,
            "name": name,
            "mobile": mobile,
            "village": village,
            "post": post,
            "gp": gp,
            "pin": pin,
            "district": district,
            "state": state,
            "aadhar_file": aadhar_filename,
            "ror_file": ror_filename,
            "father_aadhaar_file": father_filename,
            "applicant_photo": photo_filename,
            "status": "Pending"
        }

        data.append(application)
        save_data(data)

        return redirect("/thanks")

    except Exception as e:
        return f"Error submitting form: {str(e)}", 500

# ---------------------------------------------------
@app.route("/thanks")
def thanks():
    return render_template("thanks.html")

# ---------------------------------------------------
@app.route("/admin")
def admin_page():
    data = load_data()
    return render_template("admin.html", applications=data)

@app.route("/update_status", methods=["POST"])
def update_status():
    try:
        app_id = int(request.form.get("id"))
        new_status = request.form.get("status")
        data = load_data()
        for app_data in data:
            if app_data["id"] == app_id:
                app_data["status"] = new_status
                break
        save_data(data)
        flash(f"Application ID {app_id} updated to '{new_status}' successfully!")
        return redirect("/admin")
    except Exception as e:
        return f"Error updating status: {str(e)}", 500

# ---------------------------------------------------
@app.route("/status")
def status_page():
    return render_template("status.html")

@app.route("/check_status", methods=["POST"])
def check_status():
    mobile = request.form.get("mobile")
    data_list = load_data()
    result = None
    for app_data in data_list:
        if app_data["mobile"] == mobile:
            result = app_data
            break
    return render_template("status.html", data=result, mobile=mobile)

# ---------------------------------------------------
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ---------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
