from flask import Flask, render_template, request, send_file, redirect, abort
import qrcode
import os
import json
from datetime import datetime
import random
import string
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

TRACKER_FILE = 'qr_tracker.json'
REDIRECTS_FILE = 'redirects.json'
QR_FOLDER = 'qr_codes'
os.makedirs(QR_FOLDER, exist_ok=True)

# Load counter
if os.path.exists(TRACKER_FILE):
    with open(TRACKER_FILE) as f:
        tracker = json.load(f)
else:
    tracker = {"count": 0}

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
            return render_template("index.html", count=tracker["count"], qr_filename=None, error=error)

        # Load existing redirects
        if os.path.exists(REDIRECTS_FILE):
            with open(REDIRECTS_FILE) as f:
                redirects = json.load(f)
        else:
            redirects = {}

        # Generate unique code
        code = generate_code()
        while code in redirects:
            code = generate_code()

        # Save the URL and name
        redirects[code] = {
            "url": real_url,
            "name": qr_name
        }
        with open(REDIRECTS_FILE, "w") as f:
            json.dump(redirects, f)

        # Create the redirect URL for QR code
        redirect_url = request.host_url + "r/" + code
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        qr_filename = f"{timestamp}.png"
        qr_path = os.path.join(QR_FOLDER, qr_filename)

        # Generate QR code image
        qr_img = qrcode.make(redirect_url)
        qr_img.save(qr_path)

        # Add the qr_name text below the QR code image using Pillow
        qr_img = Image.open(qr_path)

        font_size = 20
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

        text = qr_name
        draw = ImageDraw.Draw(qr_img)
        
        # Use textbbox instead of textsize (fix for Pillow >= 8.0.0)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Create new image with extra space for text below
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

        tracker["count"] += 1
        with open(TRACKER_FILE, "w") as f:
            json.dump(tracker, f)

    return render_template("index.html", count=tracker["count"], qr_filename=qr_filename, qr_name=qr_name, error=error)

@app.route("/qr/<filename>")
def qr_image(filename):
    return send_file(os.path.join(QR_FOLDER, filename), mimetype='image/png')

@app.route("/r/<code>")
def redirect_short_url(code):
    if os.path.exists(REDIRECTS_FILE):
        with open(REDIRECTS_FILE) as f:
            redirects = json.load(f)
    else:
        redirects = {}

    entry = redirects.get(code)
    if entry:
        return redirect(entry["url"])
    else:
        abort(404)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
