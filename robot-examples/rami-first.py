#!/usr/bin/env python3
import sys, time
import numpy as np
import cv2

def overlay_stats(img, space_label):
    # img is RGB for PiCamera2, BGR for OpenCV capture (we’ll label accordingly)
    h, w = img.shape[:2]
    disp = img.copy()
    # Compute per-channel means
    means = img.reshape(-1, 3).mean(axis=0)
    text = f"{space_label} means: [{means[0]:.0f}, {means[1]:.0f}, {means[2]:.0f}]"
    # Contrast-safe text box
    cv2.rectangle(disp, (8, 8), (8 + 420, 8 + 60), (0, 0, 0), -1)
    cv2.putText(disp, text, (16, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2, cv2.LINE_AA)
    return disp, means

def stack_h(img_left, img_right):
    h = min(img_left.shape[0], img_right.shape[0])
    img_left  = cv2.resize(img_left,  (int(img_left.shape[1]  * h/img_left.shape[0]),  h))
    img_right = cv2.resize(img_right, (int(img_right.shape[1] * h/img_right.shape[0]), h))
    return np.hstack([img_left, img_right])

def run_picamera2():
    from picamera2 import Picamera2
    picam2 = Picamera2()

    # Use RGB888 so frames come as RGB (not YUV)
    config = picam2.create_preview_configuration(main={"size": (1280, 720), "format": "RGB888"})
    picam2.configure(config)

    # Start with AWB enabled; we’ll optionally tweak ColourGains
    try:
        picam2.set_controls({"AwbEnable": True})
    except Exception:
        pass

    picam2.start()
    time.sleep(0.5)

    # Manual gains presets to test AWB issues (rGain, bGain)
    gains_list = [
        None,          # None => leave AWB auto
        (1.0, 1.0),    # neutral manual
        (1.5, 1.0),    # boost red
        (1.0, 1.5),    # boost blue (for comparison)
        (2.0, 1.2),    # stronger red
        (1.2, 2.0),    # stronger blue
    ]
    gains_idx = 0
    manual_mode = False

    print("[PiCamera2] Keys: q=quit, c=toggle compare, g=cycle gains, a=toggle auto/manual AWB, s=save frame")
    compare = True
    saved_count = 0

    while True:
        frame = picam2.capture_array()  # RGB
        if frame is None:
            continue

        # Left: raw RGB from PiCamera2; Right: what it would look like if someone treated it as BGR
        left, lmeans = overlay_stats(frame, "RGB")
        right_bgr_view = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        right, rmeans = overlay_stats(right_bgr_view, "BGR view")

        disp = stack_h(left, right) if compare else left

        # Quick dominance hint
        hint = ""
        if lmeans[2] < 0.6*max(lmeans[0], lmeans[1]):  # blue much lower than R/G in RGB
            hint = "Hint: BLUE low in RGB (normal if scene warm)."
        elif lmeans[0] > 1.4*max(lmeans[1], lmeans[2]):  # Red dominant
            hint = "Hint: RED very high — AWB/gains?"
        elif lmeans[2] > 1.4*max(lmeans[0], lmeans[1]):
            hint = "Hint: BLUE very high — AWB/gains?"

        if hint:
            cv2.putText(disp, hint, (16, disp.shape[0]-20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2, cv2.LINE_AA)

        cv2.imshow("PiCamera2 Diagnostics", disp)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        elif key == ord('c'):
            compare = not compare
        elif key == ord('s'):
            fname = f"frame_{saved_count}.png"
            cv2.imwrite(fname, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            print(f"Saved {fname}")
            saved_count += 1
        elif key == ord('a'):
            manual_mode = not manual_mode
            if manual_mode:
                try:
                    picam2.set_controls({"AwbEnable": False})
                    # Apply current gains preset when entering manual
                    g = gains_list[gains_idx]
                    if g is not None:
                        picam2.set_controls({"ColourGains": g})
                    print(f"[PiCamera2] Manual WB ON. Gains={g}")
                except Exception as e:
                    print("Failed to disable AWB / set gains:", e)
            else:
                try:
                    picam2.set_controls({"AwbEnable": True})
                    print("[PiCamera2] Auto WB ON")
                except Exception as e:
                    print("Failed to enable AWB:", e)
        elif key == ord('g'):
            gains_idx = (gains_idx + 1) % len(gains_list)
            if manual_mode:
                g = gains_list[gains_idx]
                try:
                    if g is None:
                        print("[PiCamera2] Leaving manual mode requires 'a' to re-enable AWB; staying manual.")
                    else:
                        picam2.set_controls({"ColourGains": g})
                        print(f"[PiCamera2] Manual gains set to {g}")
                except Exception as e:
                    print("Failed to set ColourGains:", e)

    picam2.stop()
    cv2.destroyAllWindows()

def run_opencv():
    # Fallback path if PiCamera2 isn't available
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Could not open /dev/video0 with OpenCV.")
        sys.exit(1)

    print("[OpenCV] Keys: q=quit, c=toggle compare, s=save frame")
    compare = True
    saved_count = 0

    while True:
        ok, frame_bgr = cap.read()
        if not ok:
            continue

        # Left: raw BGR; Right: RGB view (what many display pipelines expect)
        left, _ = overlay_stats(frame_bgr, "BGR")
        rgb_view = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        right, _ = overlay_stats(rgb_view, "RGB view")

        disp = stack_h(left, right) if compare else left
        cv2.imshow("OpenCV Diagnostics", disp)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        elif key == ord('c'):
            compare = not compare
        elif key == ord('s'):
            fname = f"frame_{saved_count}.png"
            cv2.imwrite(fname, frame_bgr)
            print(f"Saved {fname}")
            saved_count += 1

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        from picamera2 import Picamera2  # just a presence check
        print("Using PiCamera2 backend.")
        run_picamera2()
    except Exception as e:
        print("PiCamera2 not available or failed to start, falling back to OpenCV. Reason:", e)
        run_opencv()
