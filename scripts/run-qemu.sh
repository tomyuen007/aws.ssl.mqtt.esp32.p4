#!/usr/bin/env bash
# Boots MicroPython firmware in QEMU (ESP32-P4 machine), then injects
# Python scripts and a secret.json into the virtual flash filesystem.
#
# Environment variables (all optional):
#   FIRMWARE_BIN        path to firmware.bin           (default /firmware/firmware.bin)
#   SCRIPTS_DIR         directory with *.py to upload   (default /scripts)
#   HOST_SECRET         host-side secret.json path      (default /secret.json)
#   FLASH_SIZE_MB       total flash size in MiB         (default 8)
#   FS_OFFSET           littlefs partition start hex    (default 0x200000)
#   FS_SIZE_MB          littlefs partition size in MiB  (default 2)
#   MQTT_BROKER         MQTT host seen by the firmware   (default 10.0.2.2)
#   MQTT_PORT           MQTT port                        (default 1883)
#   THING_NAME          IoT thing / MQTT client ID       (default esp32p4-device-01)
#   LOCALSTACK_HOST     hostname of LocalStack           (default localstack)
#   CAMERA_PROXY_HOST   hostname of camera-proxy sidecar (default camera-proxy)
#   CAMERA_PROXY_PORT   HTTP port of camera-proxy        (default 8080)
#   SERIAL_PORT         TCP port for serial console      (default 2323)
#   GDB_PORT            TCP port for GDB stub            (default 1234)

set -euo pipefail

FIRMWARE_BIN="${FIRMWARE_BIN:-/firmware/firmware.bin}"
SCRIPTS_DIR="${SCRIPTS_DIR:-/scripts}"
HOST_SECRET="${HOST_SECRET:-/secret.json}"
FLASH_SIZE_MB="${FLASH_SIZE_MB:-8}"
FS_OFFSET="${FS_OFFSET:-0x200000}"
FS_SIZE_MB="${FS_SIZE_MB:-2}"
MQTT_BROKER="${MQTT_BROKER:-10.0.2.2}"
MQTT_PORT="${MQTT_PORT:-1883}"
THING_NAME="${THING_NAME:-esp32p4-device-01}"
LOCALSTACK_HOST="${LOCALSTACK_HOST:-localstack}"
CAMERA_PROXY_HOST="${CAMERA_PROXY_HOST:-camera-proxy}"
CAMERA_PROXY_PORT="${CAMERA_PROXY_PORT:-8080}"
SERIAL_PORT="${SERIAL_PORT:-2323}"
GDB_PORT="${GDB_PORT:-1234}"

FLASH_IMG=/tmp/flash.bin
FS_DIR=/tmp/scripts
FS_IMG=/tmp/littlefs.bin
FLASH_SIZE=$(( FLASH_SIZE_MB * 1024 * 1024 ))
FS_SIZE=$(( FS_SIZE_MB * 1024 * 1024 ))
FS_OFFSET_DEC=$(( FS_OFFSET ))

SOCAT_PIDS=()

cleanup() {
    for pid in "${SOCAT_PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
}
trap cleanup EXIT

# ── 1. Validate firmware ───────────────────────────────────────────────────────
if [[ ! -f "${FIRMWARE_BIN}" ]]; then
    echo "ERROR: firmware not found at ${FIRMWARE_BIN}"
    echo "  Run 'make build-firmware && make copy-firmware' first."
    exit 1
fi

# ── 2. MQTT relay: QEMU user-net host (10.0.2.2) -> LocalStack ───────────────
echo "==> MQTT relay  0.0.0.0:${MQTT_PORT} -> ${LOCALSTACK_HOST}:${MQTT_PORT}"
socat TCP-LISTEN:${MQTT_PORT},fork,reuseaddr \
      TCP:${LOCALSTACK_HOST}:${MQTT_PORT} &
SOCAT_PIDS+=($!)

# ── 3. Camera relay: QEMU user-net host (10.0.2.2) -> camera-proxy ───────────
echo "==> Camera relay  0.0.0.0:${CAMERA_PROXY_PORT} -> ${CAMERA_PROXY_HOST}:${CAMERA_PROXY_PORT}"
socat TCP-LISTEN:${CAMERA_PROXY_PORT},fork,reuseaddr \
      TCP:${CAMERA_PROXY_HOST}:${CAMERA_PROXY_PORT} &
SOCAT_PIDS+=($!)

# ── 4. Build flash image ───────────────────────────────────────────────────────
echo "==> Building ${FLASH_SIZE_MB}MiB flash image..."
FLASH_SIZE=${FLASH_SIZE} python3 - <<'EOF'
import os
size = int(os.environ["FLASH_SIZE"])
with open("/tmp/flash.bin", "wb") as f:
    f.write(b"\xff" * size)
EOF
dd if="${FIRMWARE_BIN}" of="${FLASH_IMG}" conv=notrunc status=none

# ── 5. Build littlefs: Python scripts + secret.json ──────────────────────────
echo "==> Preparing filesystem..."
rm -rf "${FS_DIR}" && mkdir -p "${FS_DIR}"

# Copy .py files from SCRIPTS_DIR.
# Skip secret.py (frozen in firmware) and manifest.py (build-time only).
if [[ -d "${SCRIPTS_DIR}" ]]; then
    for f in "${SCRIPTS_DIR}"/*.py; do
        base="$(basename "$f")"
        [[ "$base" == "secret.py"   ]] && continue
        [[ "$base" == "manifest.py" ]] && continue
        cp "$f" "${FS_DIR}/"
    done
fi

# Generate secret.json for the emulator.
# WiFi credentials are read from the host secret.json (mounted at HOST_SECRET).
# MQTT broker and camera URL are always overridden with emulator-specific values
# so the virtual device can reach localstack and camera-proxy via socat relays.
MQTT_BROKER="${MQTT_BROKER}" \
MQTT_PORT="${MQTT_PORT}" \
THING_NAME="${THING_NAME}" \
CAMERA_PROXY_PORT="${CAMERA_PROXY_PORT}" \
HOST_SECRET="${HOST_SECRET}" \
FS_DIR="${FS_DIR}" \
python3 - <<'PYEOF'
import json, os

host = {}
try:
    with open(os.environ["HOST_SECRET"]) as f:
        host = json.load(f)
    print("  read WiFi credentials from host secret.json")
except (OSError, IOError):
    print("  host secret.json not found, using default WiFi credentials")

secret = {
    "wifi_ssid":        host.get("wifi_ssid", "myssid"),
    "wifi_password":    host.get("wifi_password", ""),
    "mqtt_broker":      os.environ["MQTT_BROKER"],
    "mqtt_port":        int(os.environ["MQTT_PORT"]),
    "thing_name":       os.environ["THING_NAME"],
    "camera_proxy_url": "http://10.0.2.2:" + os.environ["CAMERA_PROXY_PORT"] + "/frame.jpg",
    "emulator":         True,
}

out = os.environ["FS_DIR"] + "/secret.json"
with open(out, "w") as f:
    json.dump(secret, f)
print(f"  secret.json -> wifi_ssid={secret['wifi_ssid']}  mqtt_broker={secret['mqtt_broker']}")
PYEOF

echo "==> Creating littlefs (block=4096 page=256 size=${FS_SIZE})..."
mklittlefs -c "${FS_DIR}" -b 4096 -p 256 -s "${FS_SIZE}" "${FS_IMG}"

echo "==> Injecting filesystem at offset 0x$(printf '%X' ${FS_OFFSET_DEC})..."
dd if="${FS_IMG}" of="${FLASH_IMG}" bs=1 seek="${FS_OFFSET_DEC}" conv=notrunc status=none

# ── 6. Start QEMU ─────────────────────────────────────────────────────────────
echo ""
echo "==> Launching QEMU ESP32-P4"
echo "    Serial console  : telnet localhost ${SERIAL_PORT}"
echo "                      mpremote connect socket://localhost:${SERIAL_PORT}"
echo "    GDB stub        : localhost ${GDB_PORT}"
echo "    MQTT            : 10.0.2.2:${MQTT_PORT} -> ${LOCALSTACK_HOST}:${MQTT_PORT}"
echo "    Camera          : 10.0.2.2:${CAMERA_PROXY_PORT} -> ${CAMERA_PROXY_HOST}:${CAMERA_PROXY_PORT}"
echo "    Camera preview  : http://localhost:${CAMERA_PROXY_PORT}/stream"
echo ""

# hostfwd is intentionally absent: the guest reaches localstack and camera-proxy
# by connecting to 10.0.2.2 (this container), where socat relays the traffic.
# Adding hostfwd on the same ports socat already owns causes EADDRINUSE.
exec qemu-system-riscv32 \
    -machine esp32p4 \
    -nographic \
    -drive  file="${FLASH_IMG}",if=mtd,format=raw \
    -serial tcp::${SERIAL_PORT},server=on,wait=off \
    -gdb    tcp::${GDB_PORT} \
    -nic    user,model=esp32_wifi,net=10.0.2.0/24,host=10.0.2.2,dhcpstart=10.0.2.10
