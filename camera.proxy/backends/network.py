"""
Network fetch backend — polls windows.camera.server/server.py on Windows
and re-serves its frames. Falls back to test pattern on fetch failure.
"""

import threading
import time
import urllib.request

import cv2

from .pattern import generate as pattern_frame


def start(state: dict, url: str, width: int, height: int, encode_params: list) -> None:
    """Start the network fetch thread. Writes to state."""
    print(f"camera: network mode  url={url}", flush=True)
    state["source"] = "network"
    consecutive_errors = 0

    def _loop() -> None:
        nonlocal consecutive_errors
        while True:
            try:
                with urllib.request.urlopen(url, timeout=3) as resp:
                    data = resp.read()
                if data:
                    with state["lock"]:
                        state["jpeg"] = data
                        state["frame_num"] += 1
                    consecutive_errors = 0
            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors == 1 or consecutive_errors % 30 == 0:
                    print(
                        f"camera: network fetch error ({consecutive_errors}x): {e}",
                        flush=True,
                    )
                    print(
                        "  Is windows.camera.server/server.py running on Windows?",
                        flush=True,
                    )
                img = pattern_frame(state["frame_num"], width, height)
                _, buf = cv2.imencode(".jpg", img, encode_params)
                with state["lock"]:
                    state["jpeg"] = buf.tobytes()
                    state["frame_num"] += 1
            time.sleep(0.1)

    threading.Thread(target=_loop, daemon=True).start()
