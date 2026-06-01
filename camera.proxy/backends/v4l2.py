"""
V4L2 capture backend — USB webcam forwarded into WSL2 via usbipd-win.
"""

import threading
import time

import cv2

from .pattern import generate as pattern_frame


def start(state: dict, device, width: int, height: int, encode_params: list) -> None:
    """
    Open device with the V4L2 backend and start the capture thread.
    Raises RuntimeError if the device cannot be opened.
    """
    idx = int(device) if str(device).isdigit() else device

    cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap = cv2.VideoCapture(idx)
    if not cap.isOpened():
        raise RuntimeError(
            f"V4L2 device {device!r} not available. "
            "Attach USB camera with usbipd-win or use CAMERA_SOURCE=network."
        )

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    print(f"camera: V4L2 device {device} opened ({width}×{height})", flush=True)
    state["source"] = "v4l2"

    def _loop() -> None:
        while True:
            ok, frame = cap.read()
            img = frame if ok else pattern_frame(state["frame_num"], width, height)
            _, buf = cv2.imencode(".jpg", img, encode_params)
            with state["lock"]:
                state["jpeg"] = buf.tobytes()
                state["frame_num"] += 1
            time.sleep(0.033)

    threading.Thread(target=_loop, daemon=True).start()
