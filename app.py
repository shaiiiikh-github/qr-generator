from flask import Flask, render_template, request, send_file
import qrcode
import os
import json
from datetime import datetime

app = Flask(__name__)

TRACKER_FILE = 'qr_tracker.json'
QR_FOLDER = 'qr_codes'
os.makedirs(QR_FOLDER, exist_ok=True)

# Load counter
if os.path.exists(TRACKER_FILE):
    with open(TRACKER_FILE) as f:
        tracker = json.load(f)
else:
    tracker = {"count": 0}

@app.route("/", methods=["GET", "POST"])
def index():
    qr_filename = None
    if request.method == "POST":
        data = request.form["qr_data"]
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        qr_filename = f"{timestamp}.png"
        qr_path = os.path.join(QR_FOLDER, qr_filename)
        qrcode.make(data).save(qr_path)

        tracker["count"] += 1
        with open(TRACKER_FILE, "w") as f:
            json.dump(tracker, f)

    return render_template("index.html", count=tracker["count"], qr_filename=qr_filename)

@app.route("/qr/<filename>")
def qr_image(filename):
    return send_file(os.path.join(QR_FOLDER, filename), mimetype='image/png')




if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

