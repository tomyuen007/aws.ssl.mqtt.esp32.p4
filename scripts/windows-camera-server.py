"""
Windows-side camera server — run this from Windows CMD or PowerShell.
Captures the built-in camera via DirectShow and serves JPEG over HTTP so the
Docker camera-proxy container can fetch frames at:
  http://host.docker.internal:8081/frame.jpg
  http://host.docker.internal:8081/stream     (MJPEG, open in browser)

Requirements (run once in Windows, not WSL):
  pip install opencv-python

Usage:
  python windows-camera-server.py [--index 0] [--port 8081] [--quality 85]
"""

import argparse
import io
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

try:
    import cv2
except ImportError:
    print("ERROR: opencv-python not installed.")
    print("  Run from Windows CMD/PowerShell:  pip install opencv-python")
    sys.exit(1)


def _open(index: int) -> cv2.VideoCapture:
    """Open the camera with DirectShow backend (required for built-in cameras)."""
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if cap.isOpened():
        return cap
    # Some systems need the backend omitted on first try
    cap = cv2.VideoCapture(index)
    if cap.isOpened():
        return cap
    # Try adjacent indices in case the built-in camera isn't at 0
    for alt in range(4):
        if alt == index:
            continue
        cap = cv2.VideoCapture(alt, cv2.CAP_DSHOW)
        if cap.isOpened():
            print(f"camera: index {index} unavailable, using index {alt}")
            return cap
    raise RuntimeError(
        f"No camera found at index {index}. "
        "List available cameras with:  python -c \"import cv2; "
        "[print(i, cv2.VideoCapture(i,cv2.CAP_DSHOW).isOpened()) for i in range(5)]\""
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index",   type=int, default=0,    help="Camera index (default 0)")
    ap.add_argument("--port",    type=int, default=8081,  help="HTTP port (default 8081)")
    ap.add_argument("--quality", type=int, default=85,    help="JPEG quality 1-100")
    ap.add_argument("--width",   type=int, default=640)
    ap.add_argument("--height",  type=int, default=480)
    args = ap.parse_args()

    cap = _open(args.index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # always return the latest frame

    encode_params = [cv2.IMWRITE_JPEG_QUALITY, args.quality]

    _lock   = threading.Lock()
    _latest = [b""]

    def capture_loop():
        while True:
            ok, frame = cap.read()
            if ok:
                _, buf = cv2.imencode(".jpg", frame, encode_params)
                with _lock:
                    _latest[0] = buf.tobytes()
            time.sleep(0.033)   # ~30 fps

    threading.Thread(target=capture_loop, daemon=True).start()
    time.sleep(0.1)   # let the first frame arrive

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass   # suppress per-request noise

        def do_GET(self):
            if self.path == "/frame.jpg":
                with _lock:
                    data = _latest[0]
                self.send_response(200)
                self.send_header("Content-Type",   "image/jpeg")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control",  "no-cache")
                self.end_headers()
                self.wfile.write(data)

            elif self.path == "/stream":
                self.send_response(200)
                self.send_header(
                    "Content-Type",
                    "multipart/x-mixed-replace; boundary=frame",
                )
                self.end_headers()
                try:
                    while True:
                        with _lock:
                            data = _latest[0]
                        self.wfile.write(
                            b"--frame\r\n"
                            b"Content-Type: image/jpeg\r\n"
                            b"Content-Length: " + str(len(data)).encode() + b"\r\n\r\n"
                            + data + b"\r\n"
                        )
                        time.sleep(0.1)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            elif self.path == "/health":
                body = b'{"ok":true,"source":"directshow"}'
                self.send_response(200)
                self.send_header("Content-Type",   "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            else:
                self.send_error(404)

    server = HTTPServer(("0.0.0.0", args.port), Handler)
    print(f"Windows camera server  index={args.index}  {args.width}x{args.height}")
    print(f"  http://localhost:{args.port}/frame.jpg   — single JPEG")
    print(f"  http://localhost:{args.port}/stream      — MJPEG preview")
    print(f"")
    print(f"Docker containers reach this at:")
    print(f"  http://host.docker.internal:{args.port}/frame.jpg")
    print(f"Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        cap.release()


if __name__ == "__main__":
    main()
