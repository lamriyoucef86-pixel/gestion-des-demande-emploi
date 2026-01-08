import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_upload_dir():
    if not os.path.isdir(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            birth_date TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            diploma TEXT NOT NULL,
            qualification TEXT NOT NULL,
            file_name TEXT,
            file_type TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()
    ensure_upload_dir()

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit():
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    birth_date = request.form.get("birth_date", "").strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()
    diploma = request.form.get("diploma", "").strip()
    qualification = request.form.get("qualification", "").strip()
    uploaded_file = request.files.get("file")

    if not all([first_name, last_name, birth_date, phone, address, diploma, qualification]):
        flash("يرجى ملء جميع الحقول المطلوبة")
        return redirect(url_for("index"))

    file_name = None
    file_type = None

    if uploaded_file and uploaded_file.filename:
        if allowed_file(uploaded_file.filename):
            filename = secure_filename(uploaded_file.filename)
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
            name_part, ext = os.path.splitext(filename)
            safe_name = f"{name_part}_{timestamp}{ext}"
            uploaded_file.save(os.path.join(app.config["UPLOAD_FOLDER"], safe_name))
            file_name = safe_name
            file_type = ext.lower().replace(".", "")
        else:
            flash("صيغة الملف غير مسموح بها. المسموح: png, jpg, jpeg, pdf")
            return redirect(url_for("index"))

    conn = get_connection()
    conn.execute(
        """
        INSERT INTO applications
        (first_name, last_name, birth_date, phone, address, diploma, qualification, file_name, file_type, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            first_name,
            last_name,
            birth_date,
            phone,
            address,
            diploma,
            qualification,
            file_name,
            file_type,
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()

    flash("تم إرسال طلبك بنجاح")
    return redirect(url_for("index"))

@app.route("/file/<path:filename>")
def serve_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/auth", methods=["POST"])
def auth():
    code = request.form.get("code", "").strip()
    if code == "198619":
        session["admin"] = True
        return redirect(url_for("admin"))
    flash("رمز الدخول غير صحيح")
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("index"))

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect(url_for("index"))
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, first_name, last_name, birth_date, phone, address, diploma, qualification, file_name, file_type, created_at FROM applications ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return render_template("admin.html", applications=rows)

if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
