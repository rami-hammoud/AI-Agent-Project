#!/usr/bin/env python3
# Display Cam: localhost web viewer for Raspberry Pi Camera Module 3
# Open http://localhost:8000

import time
from flask import Flask, Response, render_template_string, send_file
from picamera2 import Picamera2
import cv2
import os
from io import BytesIO

app = Flask(__name__)

# --- Camera setup ---
picam2 = Picamera2()
CONFIG = picam2.create_preview_configuration(
    main={"size": (1280, 720), "format": "RGB888"}  # tweak resolution if you want
)
picam2.configure(CONFIG)
picam2.start()
time.sleep(0.3)  # warm-up

# Enable continuous AF on Camera Module 3 (IMX708)
try:
    from libcamera import controls
    picam2.set_controls({
        "AfMode": controls.AfModeEnum.Continuous,
        "AfSpeed": controls.AfSpeedEnum.Fast
    })
    picam2.set_controls({"AfTrigger": controls.AfTrigger.Start})
except Exception:
    pass  # ok on non-CM3 sensors
    # Save a static image to serve on the webpage
    STATIC_IMAGE_PATH = "static_lara.jpg"
    if not os.path.exists(STATIC_IMAGE_PATH):
        frame = picam2.capture_array()
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.imwrite(STATIC_IMAGE_PATH, bgr)

    @app.route("/lara")
    def lara_image():
        return send_file(STATIC_IMAGE_PATH, mimetype="image/jpeg")
HTML = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Display Cam</title>
    <style>
      :root { color-scheme: dark; }
      body { margin:0; background:#0b0b0b; color:#eee; font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, 'Helvetica Neue', Arial; }
      header { padding:12px 16px; border-bottom:1px solid #222; display:flex; align-items:center; gap:12px;}
      .badge { font-size:12px; padding:2px 8px; background:#222; border-radius:999px; }
      .funny-box { margin:20px auto; max-width:640px; background:#222; padding:16px; border-radius:12px; box-shadow:0 2px 6px rgba(0,0,0,.5); }
      .funny-box h2 { margin-top:0; color:#ffcc66; }
      .wrap { display:flex; justify-content:center; align-items:center; height: calc(100vh - 250px); }
      img { max-width:100%; max-height:100%; display:block; }
      footer { position:fixed; bottom:8px; left:16px; opacity:.6; font-size:12px;}
      a { color:#9cf; text-decoration:none; }
    </style>
  </head>
  <body>
    <header>
      <div><strong>Display Cam</strong></div>
      <div class="badge">localhost</div>
      <div style="margin-left:auto; font-size:14px">
        <a href="/snapshot">snapshot</a>
      </div>
    </header>

    <div class="funny-box">
      <h2>Meet Lara Hammoud 🎉</h2>
      <p>
        Lara Hammoud, the youngest Hammoud sibling, is officially the family’s
        Chief Mischief Officer™. Known for her sharp one-liners, random dance
        breaks, and ability to steal snacks without witnesses, Lara has a PhD in
        Making Everyone Laugh. She firmly believes that serious faces are
        overrated, and if life gives you lemons, you should probably juggle them
        in front of your siblings until they beg you to stop. 🍋🤹‍♀️
      </p>
    </div>

    <div class="wrap">
      <img src="/stream" alt="camera stream" />
    </div>

    <footer>
      /stream (MJPEG) • /snapshot (JPEG) • /healthz
    </footer>
  </body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)

def mjpeg_generator(jpeg_quality=80):
    while True:
        frame = picam2.capture_array()
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        ok, jpg = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])
        if not ok:
            continue
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n")

@app.route("/stream")
def stream():
    return Response(mjpeg_generator(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/snapshot")
def snapshot():
    # fast single capture without stopping stream
    frame = picam2.capture_array()
    bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    ok, jpg = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    bio = BytesIO(jpg.tobytes())
    bio.seek(0)
    return send_file(bio, mimetype="image/jpeg", download_name="snapshot.jpg")

@app.route("/healthz")
def healthz():
    return "ok", 200

if __name__ == "__main__":
    # localhost only; switch to 0.0.0.0 to view from other devices on your LAN
    app.run(host="0.0.0.0", port=8000, threaded=True)
