from flask import Flask, render_template, request, send_file, redirect, abort
from flask_sqlalchemy import SQLAlchemy
import qrcode
import os
from datetime import datetime
import random
import string
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///qr.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

QR_FOLDER = 'qr_codes'
os.makedirs(QR_FOLDER, exist_ok=True)

# Models
class QRCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    url = db.Column(db.String(512), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Tracker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer, default=0)

with app.app_context():
    db.create_all()
    if not Tracker.query.first():
        db.session.add(Tracker(count=0))
        db.session.commit()

def generate_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.route("/", methods=["GET", "POST"])
def index():
    qr_filename = None
    qr_name = None
    error = None

    if request.method == "POST":
        real_url = request.form.get("qr_data", "").strip()
        qr_name = request.form.get("qr_name", "").strip()

        if not real_url or not qr_name:
            error = "Please enter both a name and a URL/text."
            return render_template("index.html", count=get_count(), qr_filename=None, error=error)

        code = generate_code()
        while QRCode.query.filter_by(code=code).first():
            code = generate_code()

        redirect_url = request.host_url + "r/" + code
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        qr_filename = f"{timestamp}.png"
        qr_path = os.path.join(QR_FOLDER, qr_filename)

        # Generate and save QR
        qr_img = qrcode.make(redirect_url)
        qr_img.save(qr_path)

        # Add text to QR image
        qr_img = Image.open(qr_path)
        font_size = 20
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

        text = qr_name
        draw = ImageDraw.Draw(qr_img)
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
        new_img.save(qr_path)

        # Save to database
        db.session.add(QRCode(code=code, url=real_url, name=qr_name, filename=qr_filename))
        tracker = Tracker.query.first()
        tracker.count += 1
        db.session.commit()

    return render_template("index.html", count=get_count(), qr_filename=qr_filename, qr_name=qr_name, error=error)

@app.route("/qr/<filename>")
def qr_image(filename):
    return send_file(os.path.join(QR_FOLDER, filename), mimetype='image/png')

@app.route("/r/<code>")
def redirect_short_url(code):
    qr = QRCode.query.filter_by(code=code).first()
    if qr:
        return redirect(qr.url)
    else:
        abort(404)

def get_count():
    tracker = Tracker.query.first()
    return tracker.count if tracker else 0

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
