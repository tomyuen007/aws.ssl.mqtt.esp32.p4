"""
List all available DirectShow camera indices on Windows.

Run this before server.py if you are unsure which --index to pass.

Usage:
  python list_cameras.py [--max 5]
"""

import argparse
import sys

try:
    import cv2
except ImportError:
    print("ERROR: opencv-python not installed.")
    print("  Run from Windows CMD/PowerShell:  pip install -r requirements.txt")
    sys.exit(1)


def list_cameras(max_index: int = 5) -> list[int]:
    """Probe DirectShow indices 0..max_index-1 and print which ones open."""
    print(f"Scanning camera indices 0–{max_index - 1} (DirectShow) ...\n")
    found = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            ok, _ = cap.read()
            status = "readable" if ok else "opened but no frame"
            print(f"  [{i}]  {w}x{h}  — {status}")
            found.append(i)
            cap.release()
        else:
            print(f"  [{i}]  not available")

    print()
    if found:
        print(f"Use --index {found[0]} with server.py  (or whichever index you want)")
        print(f"Example:  python server.py --index {found[0]} --port 8081")
    else:
        print("No cameras found. Make sure the camera is not in use by another app.")
    return found


def main() -> None:
    ap = argparse.ArgumentParser(
        description="List available DirectShow camera indices on Windows."
    )
    ap.add_argument(
        "--max", type=int, default=5,
        help="Number of indices to probe (default 5)"
    )
    args = ap.parse_args()
    list_cameras(args.max)


if __name__ == "__main__":
    main()
