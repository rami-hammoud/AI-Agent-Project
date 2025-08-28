#!/usr/bin/env python3
from picamera2 import Picamera2
import time

def take_picture(filename="picture.jpg"):
    """Take a standard picture with the camera without any frame alteration."""
    picam2 = Picamera2()
    
    # Use still configuration for best quality
    config = picam2.create_still_configuration()
    picam2.configure(config)
    picam2.start()
    
    # Give camera time to adjust exposure and focus
    time.sleep(2)
    
    # Capture and save the image directly
    picam2.capture_file(filename)
    picam2.stop()
    
    print(f"✅ Picture saved as {filename}")

if __name__ == "__main__":
    take_picture("picture.jpg")
