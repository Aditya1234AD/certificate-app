import os
from flask import Flask, request, render_template, redirect, url_for, flash, send_file, abort
from werkzeug.utils import secure_filename
import sqlite3
from datetime import datetime
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from io import BytesIO
from pathlib import Path
import base64
from functools import wraps

# config
app = Flask(__name__)
APP_DIR = Path(__file__).parent
UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(APP_DIR / "uploads"))
USE_S3 = os.environ.get("USE_S3", "0") == "1"
S3_BUCKET = os.environ.get("S3_BUCKET", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "adminpass")  # change in Render env
USE_RENDER_DISK = os.environ.get("USE_RENDER_DISK", "0") == "1"
RENDER_DISK_PATH = os.environ.get("RENDER_DISK_PATH", "/mnt/disks/upload")  # mount path when using Render Disk

ALLOWED_EXT = {"pdf", "png", "jpg", "jpeg", "gif"}

DB_PATH = os.environ.get("DATABASE_URL", str(APP_DIR / "data.db"))

if USE_RENDER_DISK:
    UPLOAD_FOLDER = RENDER_DISK_PATH

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "please-change-me")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB max per request (adjust as needed)

# S3 client (optional)
s3_client = None
if USE_S3:
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=AWS_REGION
    )

# DB helpers
def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS applicants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            phone TEXT,
            village TEXT,
            district TEXT,
            state TEXT,
            applied_for TEXT,
            uploaded_files TEXT, -- JSON-like comma separated filenames or S3 URLs
            created_at TEXT
        )
        """)
init_db()

def save_applicant(data: dict):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO applicants (name,email,phone,village,district,state,applied_for,uploaded_files,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (data.get("name"), data.get("email"), data.get("phone"),
             data.get("village"), data.get("district"), data.get("state"),
             data.get("applied_for"), ",".join(data.get("uploaded_files") or []),
             datetime.utcnow().isoformat())
        )

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

def upload_to_s3(file_stream, s3_key, content_type):
    try:
        s3_client.upload_fileobj(
            file_stream,
            S3_BUCKET,
            s3_key,
            ExtraArgs={"ContentType": content_type, "ACL": "private"}
        )
        # return a presigned URL (valid for e.g. 1 hour) or S3 path
        return f"s3://{S3_BUCKET}/{s3_key}"
    except (BotoCoreError, ClientError) as e:
        app.logger.error("S3 upload failed: %s", e)
        return None

def save_local(file_storage, filename):
    path = Path(app.config["UPLOAD_FOLDER"]) / filename
    file_storage.save(str(path))
    return str(path)

# Basic auth decorator for admin
def check_auth(password):
    return password == ADMIN_PASSWORD

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.password):
            return abort(401, description="Unauthorized")
        return f(*args, **kwargs)
    return decorated

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Collect form fields
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        village = request.form.get("village")
        district = request.form.get("district")
        state = request.form.get("state")
        applied_for = request.form.get("applied_for")  # "caste" or "income" or both

        files_saved = []
        # Expecting inputs named: file1, file2, file3 etc. (front-end will define)
        for key in request.files:
            fs = request.files.get(key)
            if fs and fs.filename:
                if not allowed_file(fs.filename):
                    flash(f"File not allowed: {fs.filename}", "danger")
                    return redirect(request.url)
                filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{fs.filename}")
                if USE_S3:
                    # upload to S3
                    stream = BytesIO(fs.read())
                    stream.seek(0)
                    s3_key = f"uploads/{filename}"
                    s3_res = upload_to_s3(stream, s3_key, fs.content_type or "application/octet-stream")
                    if not s3_res:
                        flash("Failed to upload file. Try again later.", "danger")
                        return redirect(request.url)
                    files_saved.append(s3_res)
                else:
                    # save to local (Render disk or ephemeral)
                    saved_path = save_local(fs, filename)
                    files_saved.append(saved_path)

        applicant = {
            "name": name, "email": email, "phone": phone,
            "village": village, "district": district, "state": state,
            "applied_for": applied_for, "uploaded_files": files_saved
        }
        save_applicant(applicant)
        return redirect(url_for("thanks"))
    return render_template("index.html")

@app.route("/thanks")
def thanks():
    return render_template("thanks.html")

@app.route("/admin")
@require_admin
def admin():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id,name,email,phone,applied_for,uploaded_files,created_at FROM applicants ORDER BY id DESC")
        rows = cur.fetchall()
    applicants = []
    for r in rows:
        applicants.append({
            "id": r[0], "name": r[1], "email": r[2], "phone": r[3],
            "applied_for": r[4], "uploaded_files": (r[5] or "").split(",") if r[5] else [],
            "created_at": r[6]
        })
    return render_template("admin.html", applicants=applicants, use_s3=USE_S3)

# Optionally serve local files (only if using local disk). On Render, prefer S3 or Persistent Disk.
@app.route("/download")
@require_admin
def download():
    path = request.args.get("path")
    if not path:
        abort(404)
    # if S3, optionally generate presigned URL (not implemented in this route)
    if USE_S3:
        # simple info: return path (s3://...) to admin for copy/paste
        return {"s3_path": path}
    # else send local file
    if not Path(path).exists():
        abort(404)
    return send_file(path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG", "0")=="1")
