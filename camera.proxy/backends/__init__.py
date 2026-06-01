"""
Select and start the appropriate capture backend based on CAMERA_SOURCE.

Usage:
    import backends
    backends.start(source, state, **kwargs)

Returns the actual source name ("v4l2", "network", or "pattern").
"""

from . import network, pattern, v4l2


def start(
    source: str,
    state: dict,
    *,
    url: str,
    device,
    width: int,
    height: int,
    encode_params: list,
) -> str:
    """
    Start the capture thread for the requested source.
    Falls back to 'pattern' if 'auto' is requested and no V4L2 device is found.
    Returns the actual source name used.
    """
    if source == "network":
        network.start(state, url, width, height, encode_params)
        return "network"

    if source in ("v4l2", "auto"):
        try:
            v4l2.start(state, device, width, height, encode_params)
            return "v4l2"
        except RuntimeError as e:
            if source == "v4l2":
                raise
            print(f"camera: {e} — falling back to test pattern", flush=True)

    pattern.start(state, width, height, encode_params)
    return "pattern"
