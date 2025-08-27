#!/usr/bin/env python3
import time, os, sys
import numpy as np

def save_png_bgr(path, arr_bgr):
    # Minimal PNG writer via OpenCV without imshow requirements
    import cv2
    cv2.imwrite(path, arr_bgr)

def summarize(tag, img, space):
    # img is array with 3 channels; `space` is a label like "RGB" or "BGR"
    means = img.reshape(-1, 3).mean(axis=0)
    print(f"[{tag}] {space} means: [{means[0]:.1f}, {means[1]:.1f}, {means[2]:.1f}]")
    return means

def run_picamera2():
    from picamera2 import Picamera2
    import cv2

    os.makedirs("diag_out", exist_ok=True)

    picam2 = Picamera2()
    config = picam2.create_preview_configuration(
        main={"size": (1280, 720), "format": "RGB888"}
    )
    picam2.configure(config)

    # Start in Auto WB
    try:
        picam2.set_controls({"AwbEnable": True})
    except Exception:
        pass

    picam2.start()
    time.sleep(0.6)

    # capture one frame on Auto WB
    frame_rgb = picam2.capture_array()  # RGB
    if frame_rgb is None:
        print("Failed to capture frame.")
        sys.exit(1)

    # Save both RGB→BGR view and raw-as-saved
    rgb_means = summarize("AUTO", frame_rgb, "RGB")

    # What it will look like in typical OpenCV display/saves (BGR):
    import cv2
    bgr_view = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
    summarize("AUTO", bgr_view, "BGR view")
    save_png_bgr("diag_out/auto_bgr.png", bgr_view)

    # Try manual gains to see if color shifts fix the blue issue
    gains_list = [
        (1.0, 1.0),   # neutral
        (1.5, 1.0),   # boost red
        (2.0, 1.2),   # stronger red
        (1.0, 1.5),   # boost blue
        (1.2, 2.0),   # stronger blue
    ]

    # Disable Auto WB and sweep gains
    try:
        picam2.set_controls({"AwbEnable": False})
        print("Auto WB OFF; testing manual ColourGains...")
        for idx, g in enumerate(gains_list):
            try:
                picam2.set_controls({"ColourGains": g})
            except Exception as e:
                print("Failed to set ColourGains:", e)
                break
            time.sleep(0.25)
            frame_rgb = picam2.capture_array()
            summarize(f"MANUAL g={g}", frame_rgb, "RGB")
            bgr_view = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            summarize(f"MANUAL g={g}", bgr_view, "BGR view")
            save_png_bgr(f"diag_out/manual_g{g[0]}_{g[1]}.png", bgr_view)
    except Exception as e:
        print("Could not disable AWB / set gains:", e)

    # restore Auto WB
    try:
        picam2.set_controls({"AwbEnable": True})
    except Exception:
        pass

    picam2.stop()
    print("\nSaved images in ./diag_out/")
    print("Files:")
    for f in sorted(os.listdir("diag_out")):
        print(" - diag_out/" + f)

if __name__ == "__main__":
    try:
        from picamera2 import Picamera2  # check availability
        run_picamera2()
    except Exception as e:
        print("PiCamera2 failed:", e)
        print("Tip: ensure 'python3-picamera2' is installed and camera is enabled.")
        sys.exit(1)
