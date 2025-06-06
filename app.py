from flask import Flask, render_template, request, send_file, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import qrcode
import os
import string
import random
from PIL import Image, ImageDraw, ImageFont

# Initialize app
app = Flask(__name__)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///qr.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Folder to save QR images
QR_FOLDER = 'qr_codes'
os.makedirs(QR_FOLDER, exist_ok=True)


# --- Database Models ---
class QRCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    url = db.Column(db.String(500))
    code = db.Column(db.String(10), unique=True)
    filename = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Tracker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer, default=0)


# --- Utility Functions ---
def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choice(characters) for _ in range(length))
        if not QRCode.query.filter_by(code=code).first():
            return code

def get_count():
    tracker = Tracker.query.first()
    return tracker.count if tracker else 0


# --- Initialize database ---
with app.app_context():
    db.create_all()
    if Tracker.query.first() is None:
        db.session.add(Tracker(count=0))
        db.session.commit()


# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def index():
    qr_filename = None
    error = None

    if request.method == "POST":
        data = request.form.get("qr_data", "").strip()
        name = request.form.get("qr_name", "").strip() or "Untitled"

        if not data:
            error = "Please enter a URL or text for the QR code."
            return render_template("index.html", count=get_count(), qr_filename=None, error=error)

        short_code = generate_short_code()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{short_code}_{timestamp}.png"
        filepath = os.path.join(QR_FOLDER, filename)

        # Generate QR code pointing to redirect route
        qr_url = request.host_url + "r/" + short_code
        qr = qrcode.make(qr_url)
        qr.save(filepath)

        # Add text (name) below the QR code image
        qr_img = Image.open(filepath)

        font_size = 20
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()

        draw = ImageDraw.Draw(qr_img)
        text = name

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        new_img_width = max(qr_img.width, text_width + 20)
        new_img_height = qr_img.height + text_height + 20
        new_img = Image.new("RGB", (new_img_width, new_img_height), "white")

        qr_x = (new_img_width - qr_img.width) // 2
        new_img.paste(qr_img, (qr_x, 0))

        draw = ImageDraw.Draw(new_img)
        text_x = (new_img_width - text_width) // 2
        text_y = qr_img.height + 5
        draw.text((text_x, text_y), text, fill="black", font=font)

        new_img.save(filepath)

        # Save to DB
        qr_record = QRCode(name=name, url=data, code=short_code, filename=filename)
        db.session.add(qr_record)

        # Update counter
        tracker = Tracker.query.first()
        tracker.count += 1
        db.session.commit()

        qr_filename = filename

    return render_template("index.html", count=get_count(), qr_filename=qr_filename, error=error)


@app.route("/qr/<filename>")
def qr_image(filename):
    return send_file(os.path.join(QR_FOLDER, filename), mimetype='image/png')


@app.route("/r/<code>")
def redirect_qr(code):
    qr_entry = QRCode.query.filter_by(code=code).first_or_404()
    return redirect(qr_entry.url)


@app.route("/admin/dashboard")
def admin_dashboard():
    qr_codes = QRCode.query.order_by(QRCode.created_at.desc()).all()
    total_count = get_count()
    return render_template("dashboard.html", qr_codes=qr_codes, total_count=total_count)


# --- Main Entry ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
