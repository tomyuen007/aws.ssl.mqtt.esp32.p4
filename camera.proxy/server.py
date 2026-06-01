"""
HTTP camera proxy — serves frames as JPEG for the ESP32-P4 QEMU emulator.

Capture modes (CAMERA_SOURCE env var):
  auto      Try V4L2 device, fall back to test pattern  (default)
  v4l2      Force V4L2 /dev/video0  (USB cam via usbipd-win)
  network   Fetch from CAMERA_URL   (Windows built-in cam via windows.camera.server/server.py)
  pattern   Always use animated test pattern

Endpoints:
  GET /frame.jpg   — latest JPEG (what MicroPython fetches every 10 s)
  GET /stream      — MJPEG stream (open in browser for live preview)
  GET /health      — {"ok":true,"source":"v4l2"|"network"|"pattern"}

Run:
  python server.py
  # or via Docker — see Dockerfile.camera-proxy
"""

import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import cv2

import backends

# ── Config ────────────────────────────────────────────────────────────────────
SOURCE       = os.environ.get("CAMERA_SOURCE", "auto").lower()
CAMERA_URL   = os.environ.get("CAMERA_URL",    "http://host.docker.internal:8081/frame.jpg")
DEVICE       = os.environ.get("CAMERA_DEVICE", "0")
WIDTH        = int(os.environ.get("CAMERA_WIDTH",  "640"))
HEIGHT       = int(os.environ.get("CAMERA_HEIGHT", "480"))
JPEG_QUALITY = int(os.environ.get("JPEG_QUALITY",  "85"))
PORT         = int(os.environ.get("PORT",           "8080"))

ENCODE_PARAMS = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]

# ── Shared state (written by capture thread, read by HTTP handler) ─────────────
_state = {
    "lock":      threading.Lock(),
    "jpeg":      b"",
    "frame_num": 0,
    "source":    "pattern",
}

# ── Start capture backend ─────────────────────────────────────────────────────
backends.start(
    SOURCE,
    _state,
    url=CAMERA_URL,
    device=DEVICE,
    width=WIDTH,
    height=HEIGHT,
    encode_params=ENCODE_PARAMS,
)
time.sleep(0.15)   # let first frame arrive before accepting requests


# ── HTTP handler ──────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass   # suppress per-request noise

    def do_GET(self):
        if self.path == "/frame.jpg":
            with _state["lock"]:
                data = _state["jpeg"]
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
                    with _state["lock"]:
                        data = _state["jpeg"]
                    self.wfile.write(
                        b"--frame\r\nContent-Type: image/jpeg\r\n"
                        b"Content-Length: " + str(len(data)).encode() + b"\r\n\r\n"
                        + data + b"\r\n"
                    )
                    time.sleep(0.1)
            except (BrokenPipeError, ConnectionResetError):
                pass

        elif self.path == "/health":
            body = (
                '{"ok":true,"source":"' + _state["source"] + '"}'
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type",   "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        else:
            self.send_error(404)


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"camera-proxy  source={_state['source']}  port={PORT}", flush=True)
    if _state["source"] == "network":
        print(f"  fetching from: {CAMERA_URL}", flush=True)
    print(f"  /frame.jpg — single JPEG", flush=True)
    print(f"  /stream    — MJPEG preview", flush=True)
    print(f"  /health    — JSON status", flush=True)
    server.serve_forever()
