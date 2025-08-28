#!/usr/bin/env python3
from picamera2 import Picamera2
import cv2, time, numpy as np

def grayworld_awb(img_rgb):
    """Simple Gray-World AWB correction on RGB image."""
    means = img_rgb.reshape(-1, 3).mean(axis=0)
    mean_gray = means.mean()
    gains = mean_gray / (means + 1e-6)
    img = img_rgb.astype(np.float32) * gains
    return np.clip(img, 0, 255).astype(np.uint8)

def take_picture(filename="picture.jpg"):
    picam2 = Picamera2()
    config = picam2.create_still_configuration(main={"size": (1280, 720), "format": "RGB888"})
    picam2.configure(config)

    # Enable auto white balance
    picam2.set_controls({"AwbEnable": True})
    picam2.start()
    time.sleep(5)  # allow AWB + exposure to stabilize

    frame_rgb = picam2.capture_array()
    picam2.stop()

    # Save original
    cv2.imwrite("raw_" + filename, cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR))

    # Save corrected
    corrected = grayworld_awb(frame_rgb)
    cv2.imwrite(filename, cv2.cvtColor(corrected, cv2.COLOR_RGB2BGR))
    print(f"✅ Saved: raw_{filename} (camera auto) and {filename} (AWB corrected)")

if __name__ == "__main__":
    take_picture("picture.jpg")
