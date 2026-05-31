#!/usr/bin/env python3
"""
Wait for the MicroPython REPL to appear on a TCP serial port, then upload
all .py files from SCRIPTS_DIR using mpremote and reset the device.

Usage:
    inject-scripts [--host HOST] [--port PORT] [--dir DIR] [--timeout SECS]

Called automatically by run-qemu.sh after QEMU starts, but can also be run
manually to re-upload scripts without restarting the emulator.
"""

import argparse
import socket
import subprocess
import sys
import time
from pathlib import Path

REPL_PROMPT = b">>>"
BOOT_TIMEOUT = 60   # seconds to wait for MicroPython to print the REPL prompt


def wait_for_repl(host: str, port: int, timeout: float) -> bool:
    """Open a raw TCP connection and scan for the MicroPython >>> prompt."""
    deadline = time.monotonic() + timeout
    print(f"  waiting for MicroPython REPL on {host}:{port} …", flush=True)
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2) as s:
                buf = b""
                s.settimeout(2)
                while time.monotonic() < deadline:
                    try:
                        chunk = s.recv(256)
                        if not chunk:
                            break
                        buf += chunk
                        sys.stdout.buffer.write(chunk)
                        sys.stdout.buffer.flush()
                        if REPL_PROMPT in buf:
                            print("\n  REPL ready.", flush=True)
                            return True
                    except socket.timeout:
                        pass
        except (ConnectionRefusedError, OSError):
            time.sleep(1)
    return False


def upload_scripts(host: str, port: int, scripts_dir: Path) -> None:
    """Use mpremote to copy every .py file and then reset."""
    connect = f"socket://{host}:{port}"
    py_files = sorted(scripts_dir.glob("*.py"))
    if not py_files:
        print("  no .py files to upload", flush=True)
        return

    for src in py_files:
        dst = f":{src.name}"
        cmd = ["mpremote", "connect", connect, "cp", str(src), dst]
        print(f"  uploading {src.name} → {dst}", flush=True)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  WARNING: upload failed — {result.stderr.strip()}", flush=True)

    print("  resetting device…", flush=True)
    subprocess.run(
        ["mpremote", "connect", connect, "reset"],
        capture_output=True,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host",    default="localhost")
    ap.add_argument("--port",    type=int, default=2323)
    ap.add_argument("--dir",     default="/scripts")
    ap.add_argument("--timeout", type=float, default=BOOT_TIMEOUT)
    args = ap.parse_args()

    scripts_dir = Path(args.dir)
    if not scripts_dir.is_dir():
        print(f"ERROR: scripts dir not found: {scripts_dir}", file=sys.stderr)
        sys.exit(1)

    if not wait_for_repl(args.host, args.port, args.timeout):
        print("ERROR: timed out waiting for REPL", file=sys.stderr)
        sys.exit(1)

    upload_scripts(args.host, args.port, scripts_dir)
    print("Done — device is running.", flush=True)


if __name__ == "__main__":
    main()
