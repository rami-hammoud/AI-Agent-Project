#!/usr/bin/env python3
"""
cam_headless_diag.py — Headless camera color diagnostic for Raspberry Pi

What it does:
- Uses PiCamera2 if available (RGB888), otherwise falls back to OpenCV /dev/video0.
- Captures an AUTO-WB frame and a sweep of manual ColourGains.
- Saves BGR PNGs to a timestamped folder for easy scp viewing.
- Prints and writes per-channel stats and a simple verdict.

Usage examples:
  python3 cam_headless_diag.py
  python3 cam_headless_diag.py --width 1280 --height 720 --sweep
  python3 cam_headless_diag.py --no-sweep --vflip --hflip
"""

import os
import sys
import time
import math
import json
import argparse
from datetime import datetime

import numpy as np

# Optional imports are inside functions to tolerate missing libs.


def now_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_outdir(base="diag_out"):
    d = os.path.join(base, now_stamp())
    os.makedirs(d, exist_ok=True)
    return d


def stats_rgb(img_rgb):
    """
    img_rgb: HxWx3 RGB uint8
    Returns mean/std per channel and dominance heuristics.
    """
    arr = img_rgb.reshape(-1, 3).astype(np.float32)
    means = arr.mean(axis=0)             # [R,G,B] means
    stds  = arr.std(axis=0)              # [R,G,B] stds
    # Dominance heuristics (simple; robust enough for diagnostics)
    dominant = int(np.argmax(means))     # 0=R,1=G,2=B
    ratios = means / (means.mean() + 1e-6)
    return {
        "means_rgb": means.tolist(),
        "stds_rgb": stds.tolist(),
        "dominant": ["R", "G", "B"][dominant],
        "ratios_to_mean": ratios.tolist(),
    }


def verdict_from_stats(s):
    r, g, b = s["means_rgb"]
    # If blue >> others (by ~40%+), likely AWB/gains or channel swap elsewhere.
    # If AUTO looks normal but your app looks blue, your app needs RGB->BGR conversion.
    msgs = []
    if b > 1.4 * max(r, g):
        msgs.append("Blue much higher than R/G → AWB or gains issue likely.")
    if r > 1.4 * max(g, b):
        msgs.append("Red much higher than G/B → Scene warm or gains skewed.")
    if not msgs:
        msgs.append("Channel means look balanced for typical indoor light.")
    return " ".join(msgs)


def save_png_bgr(path, bgr):
    import cv2  # local import
    cv2.imwrite(path, bgr)


def to_bgr(img_rgb):
    # RGB -> BGR without cv2 (to avoid dependency if unavailable)
    return img_rgb[..., ::-1]


def capture_picamera2(width, height, vflip, hflip, gains=None, awb=True):
    """
    Returns RGB888 frame (HxWx3 uint8) using PiCamera2.
    If gains=(rGain,bGain) and awb=False, sets manual ColourGains.
    """
    from picamera2 import Picamera2

    picam2 = Picamera2()

    fmt = {"size": (width, height), "format": "RGB888"}
    config = picam2.create_preview_configuration(main=fmt)
    picam2.configure(config)

    try:
        picam2.set_controls({"AwbEnable": bool(awb)})
    except Exception:
        pass

    if not awb and gains is not None:
        try:
            picam2.set_controls({"ColourGains": gains})
        except Exception:
            pass

    picam2.start()
    time.sleep(0.5)

    frame = picam2.capture_array()  # RGB888
    picam2.stop()

    if frame is None:
        return None

    # Optional flips
    if vflip:
        frame = np.flipud(frame)
    if hflip:
        frame = np.fliplr(frame)

    return frame


def capture_opencv(width, height, vflip, hflip):
    """
    Returns RGB frame using OpenCV /dev/video0 (converted from BGR).
    """
    import cv2
    cap = cv2.VideoCapture(0)
    if width or height:
        if width:  cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
        if height: cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    ok, bgr = cap.read()
    cap.release()
    if not ok or bgr is None:
        return None
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    if vflip:
        rgb = np.flipud(rgb)
    if hflip:
        rgb = np.fliplr(rgb)
    return rgb


def main():
    ap = argparse.ArgumentParser(description="Headless camera color diagnostic")
    ap.add_argument("--width",  type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--vflip", action="store_true", help="Vertical flip")
    ap.add_argument("--hflip", action="store_true", help="Horizontal flip")
    ap.add_argument("--sweep", action="store_true", help="Also save manual ColourGains sweep (PiCamera2)")
    ap.add_argument("--no-sweep", dest="sweep", action="store_false")
    ap.set_defaults(sweep=True)
    args = ap.parse_args()

    outdir = ensure_outdir()
    print(f"[diag] Output directory: {outdir}")

    # Try PiCamera2 first
    use_picam2 = False
    try:
        import importlib
        importlib.import_module("picamera2")
        use_picam2 = True
        print("[diag] Using PiCamera2 backend.")
    except Exception as e:
        print("[diag] PiCamera2 not available, falling back to OpenCV:", e)

    # 1) AUTO WB capture
    if use_picam2:
        rgb = capture_picamera2(args.width, args.height, args.vflip, args.hflip, gains=None, awb=True)
    else:
        rgb = capture_opencv(args.width, args.height, args.vflip, args.hflip)

    if rgb is None:
        print("[error] Failed to capture an image.")
        sys.exit(1)

    bgr = to_bgr(rgb)
    auto_png = os.path.join(outdir, "auto_bgr.png")
    save_png_bgr(auto_png, bgr)
    s = stats_rgb(rgb)
    v = verdict_from_stats(s)

    print("\n[AUTO] channel means RGB: [%.1f, %.1f, %.1f]" % tuple(s["means_rgb"]))
    print("[AUTO] verdict:", v)
    print(f"[AUTO] saved: {auto_png}")

    # Write summary JSON
    summary = {
        "backend": "picamera2" if use_picam2 else "opencv",
        "width": args.width,
        "height": args.height,
        "vflip": args.vflip,
        "hflip": args.hflip,
        "auto_stats": s,
        "auto_verdict": v,
        "files": [os.path.basename(auto_png)],
    }

    # 2) Optional manual ColourGains sweep (PiCamera2 only)
    if args.sweep and use_picam2:
        print("\n[diag] Sweeping manual ColourGains with AWB OFF...")
        gains_list = [
            (1.0, 1.0),   # neutral
            (1.5, 1.0),   # boost red
            (2.0, 1.2),   # strong red
            (1.0, 1.5),   # boost blue
            (1.2, 2.0),   # strong blue
        ]
        sweep_results = []

        # Disable AWB for sweep by passing awb=False
        for g in gains_list:
            rgb_m = capture_picamera2(args.width, args.height, args.vflip, args.hflip, gains=g, awb=False)
            if rgb_m is None:
                print("[warn] Failed to capture for gains", g)
                continue
            bgr_m = to_bgr(rgb_m)
            fname = f"manual_g{g[0]:.1f}_{g[1]:.1f}.png".replace(".", "p")
            fpath = os.path.join(outdir, fname)
            save_png_bgr(fpath, bgr_m)
            st = stats_rgb(rgb_m)
            vd = verdict_from_stats(st)
            sweep_results.append({"gains": g, "stats": st, "verdict": vd, "file": fname})
            summary["files"].append(fname)
            print("[MANUAL] gains=%s means RGB: [%.1f, %.1f, %.1f] -> %s" %
                  (g, st["means_rgb"][0], st["means_rgb"][1], st["means_rgb"][2], vd))

        summary["manual_sweep"] = sweep_results

    # 3) Write summary files
    with open(os.path.join(outdir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    with open(os.path.join(outdir, "summary.txt"), "w") as f:
        f.write("Headless Camera Diagnostic Summary\n")
        f.write(f"Output dir: {outdir}\n")
        f.write(f"Backend   : {'picamera2' if use_picam2 else 'opencv'}\n")
        f.write(f"Resolution: {args.width}x{args.height}\n")
        f.write(f"Flips     : vflip={args.vflip} hflip={args.hflip}\n\n")
        f.write("[AUTO]\n")
        f.write("means RGB : [%.1f, %.1f, %.1f]\n" % tuple(summary["auto_stats"]["means_rgb"]))
        f.write("verdict   : %s\n" % summary["auto_verdict"])
        f.write("file      : auto_bgr.png\n\n")
        if "manual_sweep" in summary:
            f.write("[MANUAL SWEEP] (AWB OFF)\n")
            for item in summary["manual_sweep"]:
                r, g, b = item["stats"]["means_rgb"]
                f.write("gains=%s -> means RGB [%.1f, %.1f, %.1f] | %s | %s\n" %
                        (item["gains"], r, g, b, item["verdict"], item["file"]))
        f.write("\nNotes:\n")
        f.write("- If auto_bgr.png looks NORMAL, hardware/AWB are fine. If your app still looks blue, it’s a channel swap—convert RGB→BGR before OpenCV display/encode.\n")
        f.write("- If all images look heavily blue (B >> R/G), try warmer lighting, or keep AWB ON in your app.\n")

    print(f"\n[done] Wrote {len(summary['files'])} image(s). See {outdir}/summary.txt")


if __name__ == "__main__":
    main()
