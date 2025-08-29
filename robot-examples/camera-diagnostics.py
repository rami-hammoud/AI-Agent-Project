import subprocess
# Try new name first, fall back to old one
for cmd in (["rpicam-still", "-o", "test.jpg"],
            ["libcamera-still", "-o", "test.jpg"]):
    try:
        subprocess.run(cmd, check=True)
        print("Picture saved as test.jpg")
        break
    except FileNotFoundError:
        continue
