#!/usr/bin/env python3
"""
HTTP camera proxy — serves frames as JPEG for the ESP32-P4 QEMU emulator.

Capture modes (CAMERA_SOURCE env var):
  auto      Try V4L2 device, fall back to test pattern  (default)
  v4l2      Force V4L2 /dev/video0  (USB cam via usbipd-win)
  network   Fetch from CAMERA_URL   (Windows built-in cam via windows.camera.server/server.py)
  pattern   Always use animated test pattern

Endpoints:
  GET /frame.jpg   — latest JPEG (what MicroPython fetches)
  GET /stream      — MJPEG stream (open in browser for live preview)
  GET /health      — {"ok":true,"source":"v4l2"|"network"|"pattern"}
"""

import os
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

import cv2
import numpy as np

# ── Config ────────────────────────────────────────────────────────────────────
SOURCE       = os.environ.get("CAMERA_SOURCE", "auto").lower()
CAMERA_URL   = os.environ.get("CAMERA_URL",    "http://host.docker.internal:8081/frame.jpg")
DEVICE       = os.environ.get("CAMERA_DEVICE", "0")
WIDTH        = int(os.environ.get("CAMERA_WIDTH",  "640"))
HEIGHT       = int(os.environ.get("CAMERA_HEIGHT", "480"))
JPEG_QUALITY = int(os.environ.get("JPEG_QUALITY",  "85"))
PORT         = int(os.environ.get("PORT",           "8080"))

ENCODE_PARAMS = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]

# ── Shared state ──────────────────────────────────────────────────────────────
_frame_lock   = threading.Lock()
_latest_jpeg: bytes = b""
_frame_num    = 0
_active_source = "pattern"   # updated once capture starts


# ── Test pattern ──────────────────────────────────────────────────────────────
def _test_pattern(n: int) -> np.ndarray:
    img = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    colors = [
        (255,255,255),(255,255,0),(0,255,255),(0,255,0),
        (255,0,255),  (255,0,0),  (0,0,255),  (0,0,0),
    ]
    w = WIDTH // len(colors)
    for i, c in enumerate(colors):
        img[:, i*w:(i+1)*w] = c
    y = (n * 4) % HEIGHT
    img[y:y+4, :] = (200, 200, 200)
    cv2.putText(img, f"ESP32-P4 SIM  frame={n}",
                (10, HEIGHT - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 2)
    return img


# ── V4L2 capture loop ─────────────────────────────────────────────────────────
def _v4l2_loop(cap: cv2.VideoCapture) -> None:
    global _latest_jpeg, _frame_num, _active_source
    _active_source = "v4l2"
    while True:
        ok, frame = cap.read()
        img = frame if ok else _test_pattern(_frame_num)
        _, buf = cv2.imencode(".jpg", img, ENCODE_PARAMS)
        with _frame_lock:
            _latest_jpeg = buf.tobytes()
            _frame_num  += 1
        time.sleep(0.033)


# ── Network fetch loop (Windows built-in camera) ──────────────────────────────
def _network_loop() -> None:
    global _latest_jpeg, _frame_num, _active_source
    print(f"camera: network mode  url={CAMERA_URL}", flush=True)
    _active_source = "network"
    consecutive_errors = 0
    while True:
        try:
            with urllib.request.urlopen(CAMERA_URL, timeout=3) as resp:
                data = resp.read()
            if data:
                with _frame_lock:
                    _latest_jpeg = data
                    _frame_num  += 1
                consecutive_errors = 0
        except Exception as e:
            consecutive_errors += 1
            if consecutive_errors == 1 or consecutive_errors % 30 == 0:
                print(f"camera: network fetch error ({consecutive_errors}x): {e}",
                      flush=True)
                print(f"  Is windows.camera.server/server.py running on Windows?",
                      flush=True)
            # Fall back to test pattern frame
            img = _test_pattern(_frame_num)
            _, buf = cv2.imencode(".jpg", img, ENCODE_PARAMS)
            with _frame_lock:
                _latest_jpeg = buf.tobytes()
                _frame_num  += 1
        time.sleep(0.1)   # 10 fps is plenty for the emulator


# ── Pattern-only loop ─────────────────────────────────────────────────────────
def _pattern_loop() -> None:
    global _latest_jpeg, _frame_num, _active_source
    _active_source = "pattern"
    while True:
        img = _test_pattern(_frame_num)
        _, buf = cv2.imencode(".jpg", img, ENCODE_PARAMS)
        with _frame_lock:
            _latest_jpeg = buf.tobytes()
            _frame_num  += 1
        time.sleep(0.033)


# ── Start the right capture backend ───────────────────────────────────────────
def _start_capture() -> None:
    if SOURCE == "network":
        threading.Thread(target=_network_loop, daemon=True).start()
        return

    if SOURCE in ("v4l2", "auto"):
        idx  = int(DEVICE) if str(DEVICE).isdigit() else DEVICE
        cap  = cv2.VideoCapture(idx, cv2.CAP_V4L2)
        if not cap.isOpened():
            cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            print(f"camera: V4L2 device {DEVICE} opened ({WIDTH}×{HEIGHT})",
                  flush=True)
            threading.Thread(target=_v4l2_loop, args=(cap,), daemon=True).start()
            return
        if SOURCE == "v4l2":
            raise RuntimeError(f"V4L2 device {DEVICE} not available. "
                               "Attach USB camera with usbipd-win or use "
                               "CAMERA_SOURCE=network for the built-in camera.")
        print(f"camera: V4L2 device {DEVICE} not found — test pattern", flush=True)

    threading.Thread(target=_pattern_loop, daemon=True).start()


_start_capture()
time.sleep(0.15)   # let first frame arrive before accepting requests


# ── HTTP server ───────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == "/frame.jpg":
            with _frame_lock:
                data = _latest_jpeg
            self.send_response(200)
            self.send_header("Content-Type",   "image/jpeg")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control",  "no-cache")
            self.end_headers()
            self.wfile.write(data)

        elif self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type",
                             "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            try:
                while True:
                    with _frame_lock:
                        data = _latest_jpeg
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
                '{"ok":true,"source":"' + _active_source + '"}'
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type",   "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        else:
            self.send_error(404)


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"camera-proxy  source={SOURCE}  port={PORT}", flush=True)
    if SOURCE == "network":
        print(f"  fetching from: {CAMERA_URL}", flush=True)
    print(f"  /frame.jpg — single JPEG", flush=True)
    print(f"  /stream    — MJPEG preview", flush=True)
    server.serve_forever()
