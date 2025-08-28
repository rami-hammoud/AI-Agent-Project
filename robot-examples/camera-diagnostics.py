#!/usr/bin/env python3
"""
cam_headless_diag_v2.py — Headless camera color diagnostic (single Picamera2 session)

- Opens PiCamera2 ONCE, captures AUTO-WB, then (optionally) sweeps manual ColourGains.
- Saves BGR PNGs and writes a summary report in a timestamped folder.
- Works over SSH; no GUI needed.

Usage:
  python3 cam_headless_diag_v2.py
  python3 cam_headless_diag_v2.py --width 1920 --height 1080 --sweep
  python3 cam_headless_diag_v2.py --no-sweep --vflip --hflip
"""

import os, sys, time, json, argparse
from datetime import datetime
import numpy as np

def now_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def ensure_outdir(base="diag_out"):
    d = os.path.join(base, now_stamp())
    os.makedirs(d, exist_ok=True)
    return d

def to_bgr(img_rgb):
    return img_rgb[..., ::-1]

def save_png_bgr(path, bgr):
    import cv2
    cv2.imwrite(path, bgr)

def stats_rgb(img_rgb):
    arr = img_rgb.reshape(-1, 3).astype(np.float32)
    means = arr.mean(axis=0)  # [R,G,B]
    stds  = arr.std(axis=0)
    ratios = means / (means.mean() + 1e-6)
    dominant = ["R","G","B"][int(np.argmax(means))]
    return {
        "means_rgb": means.tolist(),
        "stds_rgb": stds.tolist(),
        "ratios_to_mean": ratios.tolist(),
        "dominant": dominant,
    }

def verdict_from_stats(s):
    r,g,b = s["means_rgb"]
    if b > 1.4 * max(r,g):
        return "Blue >> others — likely AWB/gains issue."
    if r > 1.4 * max(g,b):
        return "Red >> others — warm scene or gains skew."
    return "Channels look reasonably balanced."

def init_picam2(width, height, awb=True):
    from picamera2 import Picamera2
    picam2 = Picamera2()
    cfg = picam2.create_preview_configuration(main={"size": (width, height), "format": "RGB888"})
    picam2.configure(cfg)
    try:
        picam2.set_controls({"AwbEnable": bool(awb)})
    except Exception:
        pass
    picam2.start()
    time.sleep(0.5)
    return picam2

def capture_rgb(picam2, vflip=False, hflip=False):
    frame = picam2.capture_array()  # RGB888
    if frame is None:
        return None
    if vflip:
        frame = np.flipud(frame)
    if hflip:
        frame = np.fliplr(frame)
    return frame

def main():
    ap = argparse.ArgumentParser(description="Headless camera color diagnostic (single Picamera2 session)")
    ap.add_argument("--width",  type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--vflip", action="store_true")
    ap.add_argument("--hflip", action="store_true")
    ap.add_argument("--sweep", action="store_true", help="Sweep manual ColourGains with AWB OFF")
    ap.add_argument("--no-sweep", dest="sweep", action="store_false")
    ap.set_defaults(sweep=True)
    args = ap.parse_args()

    outdir = ensure_outdir()
    print(f"[diag] Output directory: {outdir}")

    # Ensure nothing else is using the camera (close PiCrawler/Vilib if running).
    try:
        from picamera2 import Picamera2  # just to check availability
    except Exception as e:
        print("[error] PiCamera2 not available:", e)
        sys.exit(1)

    # Open ONE camera session
    try:
        picam2 = init_picam2(args.width, args.height, awb=True)
    except Exception as e:
        print("[error] Failed to open camera:", e)
        sys.exit(1)

    files = []
    summary = {
        "backend": "picamera2",
        "width": args.width,
        "height": args.height,
        "vflip": args.vflip,
        "hflip": args.hflip,
        "files": files,
    }

    # AUTO WB capture
    rgb = capture_rgb(picam2, args.vflip, args.hflip)
    if rgb is None:
        print("[error] Failed to capture AUTO frame")
        picam2.stop(); sys.exit(1)

    bgr = to_bgr(rgb)
    auto_path = os.path.join(outdir, "auto_bgr.png")
    save_png_bgr(auto_path, bgr)
    s_auto = stats_rgb(rgb)
    v_auto = verdict_from_stats(s_auto)
    print("\n[AUTO] means RGB: [%.1f, %.1f, %.1f]" % tuple(s_auto["means_rgb"]))
    print("[AUTO] verdict:", v_auto)
    print("[AUTO] saved:", auto_path)
    files.append(os.path.basename(auto_path))
    summary["auto_stats"] = s_auto
    summary["auto_verdict"] = v_auto

    # Optional manual sweep — reuse the SAME camera; just toggle controls
    if args.sweep:
        print("\n[diag] Sweeping manual ColourGains with AWB OFF...")
        try:
            picam2.set_controls({"AwbEnable": False})
        except Exception as e:
            print("[warn] Could not disable AWB:", e)

        gains_list = [
            (1.0, 1.0),
            (1.5, 1.0),
            (2.0, 1.2),
            (1.0, 1.5),
            (1.2, 2.0),
        ]
        sweep = []
        for g in gains_list:
            try:
                picam2.set_controls({"ColourGains": g})
            except Exception as e:
                print("[warn] Failed to set ColourGains", g, e)
                continue
            time.sleep(0.25)
            rgb_m = capture_rgb(picam2, args.vflip, args.hflip)
            if rgb_m is None:
                print("[warn] Capture failed for gains", g)
                continue
            bgr_m = to_bgr(rgb_m)
            fname = f"manual_g{g[0]:.1f}_{g[1]:.1f}.png".replace(".", "p")
            fpath = os.path.join(outdir, fname)
            save_png_bgr(fpath, bgr_m)
            st = stats_rgb(rgb_m)
            vd = verdict_from_stats(st)
            print("[MANUAL] gains=%s -> means RGB [%.1f, %.1f, %.1f] | %s | saved %s"
                  % (g, st["means_rgb"][0], st["means_rgb"][1], st["means_rgb"][2], vd, fpath))
            files.append(fname)
            sweep.append({"gains": g, "stats": st, "verdict": vd, "file": fname})
        summary["manual_sweep"] = sweep

        # Restore AWB
        try:
            picam2.set_controls({"AwbEnable": True})
        except Exception:
            pass

    # Close camera cleanly
    picam2.stop()

    # Write summaries
    with open(os.path.join(outdir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    with open(os.path.join(outdir, "summary.txt"), "w") as f:
        f.write("Headless Camera Diagnostic (single session)\n")
        f.write(f"Output dir: {outdir}\n")
        f.write(f"Resolution: {args.width}x{args.height}\n")
        f.write(f"Flips     : vflip={args.vflip} hflip={args.hflip}\n\n")
        f.write("[AUTO]\n")
        f.write("means RGB : [%.1f, %.1f, %.1f]\n" % tuple(summary["auto_stats"]["means_rgb"]))
        f.write("verdict   : %s\n" % summary["auto_verdict"])
        f.write("file      : auto_bgr.png\n\n")
        if "manual_sweep" in summary:
            f.write("[MANUAL SWEEP] (AWB OFF)\n")
            for item in summary["manual_sweep"]:
                r,g,b = item["stats"]["means_rgb"]
                f.write("gains=%s -> means RGB [%.1f, %.1f, %.1f] | %s | %s\n" %
                        (item["gains"], r, g, b, item["verdict"], item["file"]))
        f.write("\nNotes:\n- If auto_bgr.png looks normal but your app is blue, convert RGB→BGR before OpenCV display/encode.\n")

    print(f"\n[done] Wrote {len(files)} image(s). See {outdir}/summary.txt")

if __name__ == "__main__":
    main()
