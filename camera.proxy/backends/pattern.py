"""
Test pattern backend — animated colour-bar with moving scan line and frame counter.
No physical camera required.
"""

import threading
import time

import cv2
import numpy as np

_COLOURS = [
    (255, 255, 255), (255, 255, 0), (0, 255, 255), (0, 255, 0),
    (255, 0, 255),   (255, 0, 0),   (0, 0, 255),   (0, 0, 0),
]


def generate(n: int, width: int, height: int) -> np.ndarray:
    """Return a single test-pattern frame for frame number n."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    col_w = width // len(_COLOURS)
    for i, colour in enumerate(_COLOURS):
        img[:, i * col_w:(i + 1) * col_w] = colour
    y = (n * 4) % height
    img[y:y + 4, :] = (200, 200, 200)
    cv2.putText(
        img, f"ESP32-P4 SIM  frame={n}",
        (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2,
    )
    return img


def start(state: dict, width: int, height: int, encode_params: list) -> None:
    """Start the pattern capture thread. Writes to state."""
    state["source"] = "pattern"

    def _loop() -> None:
        while True:
            img = generate(state["frame_num"], width, height)
            _, buf = cv2.imencode(".jpg", img, encode_params)
            with state["lock"]:
                state["jpeg"] = buf.tobytes()
                state["frame_num"] += 1
            time.sleep(0.033)

    threading.Thread(target=_loop, daemon=True).start()
