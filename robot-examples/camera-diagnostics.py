#!/usr/bin/env python3
from picamera2 import Picamera2
import cv2
import time

def take_picture(filename="test.jpg"):
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(
        main={"size": (1280, 720), "format": "RGB888"}
    )
    picam2.configure(config)
    picam2.start()
    time.sleep(0.5)  # give the camera time to adjust

    # Capture RGB frame
    frame_rgb = picam2.capture_array()
    picam2.stop()

    if frame_rgb is None:
        print("❌ Failed to capture image")
        return

    # Convert RGB → BGR for OpenCV before saving
    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
    cv2.imwrite(filename, frame_bgr)
    print(f"✅ Saved picture as {filename}")

if __name__ == "__main__":
    take_picture("test.jpg")
