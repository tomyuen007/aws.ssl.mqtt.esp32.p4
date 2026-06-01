"""
List available V4L2 camera devices on Linux / WSL2.

Run this before starting server.py if you are unsure which CAMERA_DEVICE to use.

Usage:
  python list_cameras.py [--max 5]
"""

import argparse
import os
import sys
from pathlib import Path

try:
    import cv2
except ImportError:
    print("ERROR: opencv-python-headless not installed.")
    print("  Run: pip install -r requirements.txt")
    sys.exit(1)


def list_v4l2(max_index: int = 5) -> list[int]:
    """Probe /dev/video0..max_index-1 and print status for each."""
    print(f"Scanning V4L2 devices /dev/video0 – /dev/video{max_index - 1} ...\n")
    found = []

    for i in range(max_index):
        path = Path(f"/dev/video{i}")
        if not path.exists():
            print(f"  [{i}]  /dev/video{i}  not present")
            continue

        cap = cv2.VideoCapture(i, cv2.CAP_V4L2)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            ok, _ = cap.read()
            status = "readable" if ok else "opened but no frame"
            print(f"  [{i}]  /dev/video{i}  {w}×{h}  — {status}")
            found.append(i)
            cap.release()
        else:
            print(f"  [{i}]  /dev/video{i}  present but not openable")

    print()
    if found:
        print(f"Use CAMERA_DEVICE={found[0]} with server.py")
        print(f"Example:  CAMERA_SOURCE=v4l2 CAMERA_DEVICE={found[0]} python server.py")
    else:
        print("No V4L2 cameras found.")
        if os.path.exists("/dev/video0"):
            print("  Hint: device exists but could not be opened — check permissions")
            print("        or attach USB camera via usbipd-win first.")
        else:
            print("  Hint: attach a USB camera with usbipd-win or use CAMERA_SOURCE=network.")

    return found


def main() -> None:
    ap = argparse.ArgumentParser(
        description="List available V4L2 camera devices on Linux / WSL2."
    )
    ap.add_argument(
        "--max", type=int, default=5,
        help="Number of /dev/videoN indices to probe (default 5)"
    )
    args = ap.parse_args()
    list_v4l2(args.max)


if __name__ == "__main__":
    main()
