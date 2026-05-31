# ESP32-P4 IoT Camera / MQTT — Local Development Stack

**Target chip:** ESP32-P4 (dual-core HP RISC-V @ 360 MHz, 768 KB SRAM, MIPI CSI-2)  
**Host:** Windows 11 + WSL2 + Docker Desktop

---

## Current status — 2026-05-30

### Completed
- [x] `Dockerfile.micropython` — ESP-IDF v5.4 + MicroPython v1.24.0 + `esp32-camera` component; compiles `firmware.bin` for `ESP32_P4_CAM` board at image build time
- [x] `Dockerfile.qemu` — Espressif QEMU from source (`esp-develop` branch, `riscv32-softmmu`, `esp32p4` machine) + `mklittlefs`
- [x] `Dockerfile.camera-proxy` — Python/OpenCV HTTP server; modes: `network` (Windows built-in camera via DirectShow), `v4l2` (USB via usbipd-win), `pattern` (test)
- [x] `Secret` class (`secret.py`) — single access point for all config; reads `secret.json` from device filesystem; frozen into firmware
- [x] `boot.py` — WiFi via `Secret.wifi_ssid()` / `Secret.wifi_password()`
- [x] `main.py` — camera capture + MQTT publish every 10 s; SSL branch when `emulator=false`
- [x] `modcamera.c` — MicroPython C module wrapping `esp_camera_*` for MIPI CSI-2
- [x] SSL/TLS on real hardware (port 8883); plain TCP in emulator (port 1883)
- [x] `setup-localstack.sh` — provisions IoT thing/policy; saves `device.pem.crt`, `device.key`, `ca.pem`
- [x] QEMU SLiRP DNS — emulator resolves `localstack` and `camera-proxy` by Docker service name via `127.0.0.11`; socat relays kept as DNS-failure fallback
- [x] `secret.json` git-ignored; `.env` committed (no secrets)
- [x] All instructions use plain `docker` CLI — no `docker compose`
- [x] GitHub repo: https://github.com/tomyuen007/aws.ssl.mqtt.esp32.p4

### Not yet tested — requires network / hardware
- [ ] `docker build` for all three custom images (network was unavailable during dev session)
- [ ] QEMU SLiRP DNS resolution in practice — `localstack` / `camera-proxy` hostnames resolve correctly inside the emulator
- [ ] MicroPython REPL via `mpremote connect socket://localhost:2323`
- [ ] Camera stream at `http://localhost:8080/stream`
- [ ] MQTT publish/subscribe verified with `mosquitto_sub`
- [ ] SSL handshake with LocalStack on port 8883 (`mqtt_ssl_verify=false`)
- [ ] Physical ESP32-P4 hardware — camera, WiFi, SSL to LocalStack and AWS IoT Core

### Resume checklist
```
1.  cp secret.json.example secret.json        # fill in wifi_ssid, wifi_password
2.  docker build -t esp32p4-camera-proxy:latest -f Dockerfile.camera-proxy .
3.  docker build -t esp32p4-micropython:latest --target builder --build-arg MPY_TAG=v1.24.0 -f Dockerfile.micropython .
4.  docker build -t esp32p4-emulator:latest -f Dockerfile.qemu .
5.  docker network create iot-net
6.  docker volume create localstack_data
7.  docker run -d --name localstack ...       # Step 4 in README
8.  docker run -d --name camera-proxy ...     # Step 5
9.  docker run -d --name micropython-builder ... # Step 6
10. docker exec micropython-builder bash -c "cp .../firmware.bin /firmware-out/"
11. AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test THING_NAME=esp32p4-device-01 bash scripts/setup-localstack.sh
12. python scripts\windows-camera-server.py --port 8081   # Windows CMD
13. docker run -d --name esp32p4-emulator ...  # Step 10 in README
14. mpremote connect socket://localhost:2323
15. mosquitto_sub -h localhost -p 1883 -t "devices/#" -v
```

---

## Decision: plain `docker` CLI — no `docker compose`

All instructions use plain `docker` commands.  
`docker-compose.yml` is kept as a reference for the service definitions but is not used to run anything.

Reasons:
- Every step is explicit and visible — no hidden orchestration
- Easier to run individual services in isolation for debugging
- No dependency on the Compose plugin version
- Container start order, health checks, and volume creation are all manual and auditable

---

## Services

| Container | Image | Ports |
|---|---|---|
| `localstack` | `localstack/localstack:latest` | 4566, 1883, 8883 |
| `camera-proxy` | `esp32p4-camera-proxy:latest` | 8080 |
| `micropython-builder` | `esp32p4-micropython:latest` | — |
| `esp32p4-emulator` | `esp32p4-emulator:latest` | 2323, 1234 |

All containers share the bridge network `iot-net`.

---

## Prerequisites — install once

**Docker Desktop for Windows**
- Enable *Use WSL 2 based engine* in Settings → General

**AWS CLI (WSL2)**
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
unzip awscliv2.zip
sudo ./aws/install
```

**mpremote (WSL2)**
```bash
pip install mpremote
```

**Python + OpenCV (Windows CMD/PowerShell — for built-in camera)**
```cmd
pip install opencv-python
```

---

## First-time setup

### Step 1 — Create secret.json

```bash
cp secret.json.example secret.json
```

Edit `secret.json` and set your real values:
```json
{
  "wifi_ssid":       "your-wifi-ssid",
  "wifi_password":   "your-wifi-password",
  "mqtt_broker":     "192.168.1.100",
  "mqtt_port":       1883,
  "mqtt_ssl_port":   8883,
  "thing_name":      "esp32p4-device-01",
  "mqtt_ssl_verify": false,
  "ca_cert":         null,
  "device_cert":     "device.pem.crt",
  "device_key":      "device.key"
}
```

`mqtt_ssl_verify` and cert paths:

| Scenario | `mqtt_ssl_verify` | `ca_cert` | notes |
|---|---|---|---|
| Emulator | n/a | n/a | always plain TCP — `emulator=true` skips SSL entirely |
| LocalStack (real hw) | `false` | `null` | self-signed cert, skip verification |
| Real AWS | `true` | `"ca.pem"` | use `AmazonRootCA1.pem` downloaded from AWS |

`secret.json` is listed in `.gitignore` — it will never be committed.

How secrets reach the firmware:
- All config is read via the `Secret` class in `secret.py` (frozen into firmware).
- **Emulator**: `run-qemu.sh` reads WiFi credentials from the host's `secret.json`
  (mounted read-only at `/secret.json`) and merges with emulator overrides
  (`mqtt_broker=localstack`, `camera_proxy_url=http://camera-proxy:8080/frame.jpg`,
  `emulator=true`), then writes
  the merged `secret.json` into the virtual flash filesystem.
- **Real hardware**: `upload-scripts` uploads `secret.json` directly to the
  device filesystem. `secret.py` reads it at runtime.

Do not edit `boot.py` or `main.py` directly for credentials.

---

### Step 2 — Create Docker network and volume

```bash
docker network create iot-net

docker volume create localstack_data
```

---

### Step 3 — Build images

Each image is built once; Docker layer cache makes rebuilds fast.

**camera-proxy** (~2 min)
```bash
docker build \
  -t esp32p4-camera-proxy:latest \
  -f Dockerfile.camera-proxy \
  .
```

**micropython-builder** (~15–30 min)  
Pulls `espressif/idf:release-v5.4`, clones MicroPython v1.24.0 and
`espressif/esp32-camera`, then compiles `firmware.bin` for ESP32-P4.
```bash
docker build \
  -t esp32p4-micropython:latest \
  --target builder \
  --build-arg MPY_TAG=v1.24.0 \
  -f Dockerfile.micropython \
  .
```

**esp32p4-emulator** (~15–20 min)  
Compiles Espressif QEMU from source (`esp-develop` branch, `riscv32-softmmu`
target with `esp32p4` machine) and builds `mklittlefs`.
```bash
docker build \
  -t esp32p4-emulator:latest \
  -f Dockerfile.qemu \
  .
```

---

### Step 4 — Start LocalStack

```bash
docker run -d \
  --name localstack \
  --network iot-net \
  -p 4566:4566 \
  -p 1883:1883 \
  -p 8883:8883 \
  -e SERVICES=iot,sts,s3 \
  -e DEBUG=1 \
  -e PERSIST_ALL=1 \
  -e LOCALSTACK_AUTH_TOKEN= \
  -v localstack_data:/var/lib/localstack \
  -v /var/run/docker.sock:/var/run/docker.sock \
  localstack/localstack:latest
```

Wait for the IoT service to be ready before continuing:
```bash
until docker exec localstack \
    curl -sf http://localhost:4566/_localstack/health | grep -q '"iot"'; do
  sleep 2
done
echo "LocalStack ready."
```

---

### Step 5 — Start camera-proxy

Default camera source is `network` (Windows built-in camera via
`windows-camera-server.py`).  See the [Camera modes](#camera-modes) section
to switch to `v4l2` (USB) or `pattern` (test pattern).

```bash
docker run -d \
  --name camera-proxy \
  --network iot-net \
  -p 8080:8080 \
  -e CAMERA_SOURCE=network \
  -e CAMERA_URL=http://host.docker.internal:8081/frame.jpg \
  -e CAMERA_DEVICE=0 \
  -e CAMERA_WIDTH=640 \
  -e CAMERA_HEIGHT=480 \
  -e JPEG_QUALITY=85 \
  -e PORT=8080 \
  --add-host host.docker.internal:host-gateway \
  esp32p4-camera-proxy:latest
```

---

### Step 6 — Start micropython-builder

The container stays alive with `tail -f /dev/null` so you can exec into it.
```bash
mkdir -p firmware-out

docker run -d \
  --name micropython-builder \
  --network iot-net \
  -v "$(pwd)/micropython/boards/ESP32_P4_CAM:/opt/micropython/ports/esp32/boards/ESP32_P4_CAM" \
  -v "$(pwd)/micropython/modules:/opt/micropython/ports/esp32/modules_camera" \
  -v "$(pwd)/micropython/src:/opt/micropython/ports/esp32/modules_frozen" \
  -v "$(pwd)/firmware-out:/firmware-out" \
  -e EXTRA_COMPONENT_DIRS=/opt/esp32-camera \
  --entrypoint tail \
  esp32p4-micropython:latest \
  -f /dev/null
```

---

### Step 7 — Copy firmware to the host

`firmware.bin` was compiled during `docker build` in Step 3 and is baked into
the image.  Copy it out to `./firmware-out/` so the emulator can mount it.

```bash
docker exec micropython-builder \
  bash -c "cp /opt/micropython/ports/esp32/build-ESP32_P4_CAM/firmware.bin \
           /firmware-out/"

ls -lh firmware-out/firmware.bin
```

---

### Step 8 — Provision IoT resources on LocalStack

```bash
AWS_ACCESS_KEY_ID=test \
AWS_SECRET_ACCESS_KEY=test \
THING_NAME=esp32p4-device-01 \
bash scripts/setup-localstack.sh
```

Creates (idempotent — safe to re-run):
- IoT Thing: `esp32p4-device-01`
- IoT Policy: `esp32p4-mqtt-policy` (connect / publish / subscribe / receive)
- Certificate: saved to `./certs/device.pem.crt`

---

### Step 9 — Start the Windows camera server (built-in camera)

Skip if using `CAMERA_SOURCE=pattern`.

**From Windows CMD or PowerShell:**
```cmd
python scripts\windows-camera-server.py --port 8081
```

**Or from WSL2** (opens a new Windows CMD window):
```bash
cmd.exe /c start "Windows Camera Server" \
  python.exe "$(wslpath -w "$(pwd)/scripts/windows-camera-server.py")" \
  --port 8081
```

When Windows Firewall prompts for network access, click **Allow**.

Verify: open `http://localhost:8081/stream` in a browser — you should see
a live feed from the built-in camera.

---

### Step 10 — Start the emulator

`firmware-out/firmware.bin` and `secret.json` must both exist before running this.

```bash
docker run -d \
  --name esp32p4-emulator \
  --network iot-net \
  -p 2323:2323 \
  -p 1234:1234 \
  -v "$(pwd)/firmware-out:/firmware:ro" \
  -v "$(pwd)/micropython/src:/scripts:ro" \
  -v "$(pwd)/secret.json:/secret.json:ro" \
  -e FIRMWARE_BIN=/firmware/firmware.bin \
  -e SCRIPTS_DIR=/scripts \
  -e HOST_SECRET=/secret.json \
  -e FLASH_SIZE_MB=8 \
  -e FS_OFFSET=0x200000 \
  -e FS_SIZE_MB=2 \
  -e MQTT_BROKER=localstack \
  -e MQTT_PORT=1883 \
  -e THING_NAME=esp32p4-device-01 \
  -e LOCALSTACK_HOST=localstack \
  -e CAMERA_PROXY_HOST=camera-proxy \
  -e CAMERA_PROXY_PORT=8080 \
  -e SERIAL_PORT=2323 \
  -e GDB_PORT=1234 \
  esp32p4-emulator:latest
```

What `run-qemu.sh` does inside the container:
1. Starts socat relays as DNS fallbacks (MQTT + camera — see note below)
2. Pads `firmware.bin` to 8 MiB (0xFF = erased NOR flash)
3. Reads WiFi credentials from `/secret.json`; merges with emulator overrides
   (`mqtt_broker=localstack`, `camera_proxy_url=http://camera-proxy:8080/frame.jpg`,
   `emulator=true`) and writes the merged `secret.json` into the littlefs
4. Copies `boot.py` / `main.py` from `/scripts` into the littlefs
   (`secret.py` is skipped — already frozen in the firmware image)
5. Injects the littlefs at flash offset `0x200000`
6. Launches `qemu-system-riscv32 -machine esp32p4`
   — serial console on TCP 2323, GDB stub on TCP 1234

> **Name resolution**: QEMU user-mode networking (SLiRP) proxies DNS through
> the container's `/etc/resolv.conf` → Docker embedded DNS (`127.0.0.11`) →
> resolves `localstack` and `camera-proxy` to their `iot-net` IPs directly.
> The socat relays handle the rare case where DNS is not yet ready at boot.

Verify the emulator started:
```bash
docker logs esp32p4-emulator
docker ps --filter name=esp32p4-emulator
```

---

### Step 11 — Attach to the MicroPython REPL

```bash
mpremote connect socket://localhost:2323
```

Press **Enter** if the `>>>` prompt does not appear immediately.  
**Ctrl-X** exits mpremote.

Alternative (raw telnet):
```bash
telnet localhost 2323
```

---

### Step 12 — Verify camera stream

Open in browser: `http://localhost:8080/stream`

Live MJPEG from your built-in camera (or animated test pattern if
`CAMERA_SOURCE=pattern`).

---

### Step 13 — Verify MQTT messages

Requires `mosquitto_sub` (`sudo apt install mosquitto-clients` in WSL2):
```bash
mosquitto_sub -h localhost -p 1883 -t "devices/#" -v
```

Expected every 10 seconds:
```
devices/esp32p4-device-01/status     {"state":"online","chip":"esp32p4",...}
devices/esp32p4-device-01/telemetry  {"thing":"...","seq":0,"img_b":12345}
devices/esp32p4-device-01/image      <binary JPEG>
```

---

## Daily workflow

```bash
# 1. Windows camera server (Windows CMD / PowerShell)
python scripts\windows-camera-server.py --port 8081

# 2. Start containers (WSL2) — skip if already running
docker start localstack camera-proxy micropython-builder

# 3. Wait for LocalStack IoT
until docker exec localstack \
    curl -sf http://localhost:4566/_localstack/health | grep -q '"iot"'; do
  sleep 2
done

# 4. Start emulator
docker start esp32p4-emulator

# 5. Attach REPL
mpremote connect socket://localhost:2323

# 6. Stop everything
docker stop esp32p4-emulator micropython-builder camera-proxy localstack
```

---

## Rebuild firmware

### Python files only (boot.py / main.py)

Re-upload to the running emulator without restarting QEMU:
```bash
docker exec esp32p4-emulator \
  inject-scripts --host localhost --port 2323 --dir /scripts
```

### C code or board files (modcamera.c, sdkconfig.board, etc.)

```bash
# Recompile inside the running builder container
docker exec micropython-builder \
  bash -c "cd /opt/micropython/ports/esp32 && \
    make BOARD=ESP32_P4_CAM \
         USER_C_MODULES=modules_camera/micropython.cmake \
         FROZEN_MANIFEST=modules_frozen/manifest.py \
         -j\$(nproc)"

# Copy new firmware to host
docker exec micropython-builder \
  bash -c "cp /opt/micropython/ports/esp32/build-ESP32_P4_CAM/firmware.bin \
           /firmware-out/"

# Restart the emulator to pick up the new firmware
docker stop esp32p4-emulator && docker rm esp32p4-emulator

docker run -d \
  --name esp32p4-emulator \
  --network iot-net \
  -p 2323:2323 \
  -p 1234:1234 \
  -v "$(pwd)/firmware-out:/firmware:ro" \
  -v "$(pwd)/micropython/src:/scripts:ro" \
  -v "$(pwd)/secret.json:/secret.json:ro" \
  -e FIRMWARE_BIN=/firmware/firmware.bin \
  -e SCRIPTS_DIR=/scripts \
  -e HOST_SECRET=/secret.json \
  -e FLASH_SIZE_MB=8 \
  -e FS_OFFSET=0x200000 \
  -e FS_SIZE_MB=2 \
  -e MQTT_BROKER=localstack \
  -e MQTT_PORT=1883 \
  -e THING_NAME=esp32p4-device-01 \
  -e LOCALSTACK_HOST=localstack \
  -e CAMERA_PROXY_HOST=camera-proxy \
  -e CAMERA_PROXY_PORT=8080 \
  -e SERIAL_PORT=2323 \
  -e GDB_PORT=1234 \
  esp32p4-emulator:latest
```

---

## Flash to physical ESP32-P4 hardware

```bash
pip install esptool

# Find the serial port
ls /dev/ttyUSB* /dev/ttyACM*

# Erase flash
esptool.py --chip esp32p4 --port /dev/ttyUSB0 erase_flash

# Flash firmware
esptool.py --chip esp32p4 --port /dev/ttyUSB0 --baud 460800 \
  --before default_reset --after hard_reset \
  write_flash --flash_mode dio --flash_size detect 0x0 \
  firmware-out/firmware.bin

# Upload secret.json + Python scripts (secret.py is frozen in firmware)
mpremote connect /dev/ttyUSB0 \
  cp secret.json :secret.json + \
  cp micropython/src/boot.py :boot.py + \
  cp micropython/src/main.py :main.py + \
  reset

# Serial monitor
mpremote connect /dev/ttyUSB0
```

Before flashing, set `mqtt_broker` in `secret.json` to your host machine's LAN IP:
```json
{
  "mqtt_broker": "192.168.1.100"
}
```

`upload-scripts` uploads `secret.json` directly to the device — do not edit
`boot.py` or `main.py` for credentials.

---

## Camera modes

| `CAMERA_SOURCE` | Camera | Setup required |
|---|---|---|
| `network` (default) | Windows built-in (Intel IPU / DirectShow) | Run `windows-camera-server.py` on Windows |
| `v4l2` | USB webcam via usbipd-win | See below; add `--device /dev/video0` to `docker run` |
| `pattern` | Animated test pattern | Nothing |

### v4l2 USB camera setup

Windows PowerShell (Administrator):
```powershell
usbipd list                        # find webcam BUS-ID e.g. 2-3
usbipd bind   --busid 2-3          # one-time per device
usbipd attach --wsl --busid 2-3    # each Windows session
```

WSL2 — confirm device appears:
```bash
ls /dev/video*
```

Replace the `camera-proxy` `docker run` command with:
```bash
docker run -d \
  --name camera-proxy \
  --network iot-net \
  -p 8080:8080 \
  --device /dev/video0:/dev/video0 \
  -e CAMERA_SOURCE=v4l2 \
  -e CAMERA_DEVICE=0 \
  -e CAMERA_WIDTH=640 \
  -e CAMERA_HEIGHT=480 \
  -e JPEG_QUALITY=85 \
  -e PORT=8080 \
  --add-host host.docker.internal:host-gateway \
  esp32p4-camera-proxy:latest
```

---

## Port reference

| Port | Service | Purpose |
|---|---|---|
| 4566 | localstack | AWS API gateway (IoT, S3, STS) |
| 1883 | localstack | MQTT plain |
| 8883 | localstack | MQTT TLS |
| 8080 | camera-proxy | `GET /frame.jpg`  `GET /stream` |
| 8081 | windows-camera-server.py | Windows side — not in Docker |
| 2323 | esp32p4-emulator | Serial REPL (mpremote / telnet) |
| 1234 | esp32p4-emulator | QEMU GDB stub |

---

## MQTT transport

| Runtime | Port | Transport |
|---|---|---|
| Emulator (`emulator=true` in secret.json) | 1883 | Plain TCP — SSL skipped |
| Real hardware → LocalStack | 8883 | TLS, server cert not verified (`mqtt_ssl_verify=false`) |
| Real hardware → AWS IoT Core | 8883 | Mutual TLS, server verified (`mqtt_ssl_verify=true`) |

Run `make setup` after containers start to provision the IoT thing and save
`certs/device.pem.crt`, `certs/device.key`, and `certs/ca.pem` (LocalStack CA).
`make upload-scripts` pushes all cert files to the device alongside `secret.json`.

---

## MQTT topics

| Topic | QoS | Direction | Payload |
|---|---|---|---|
| `devices/<THING>/status` | 1 | publish, retained | `{"state":"online","chip":"esp32p4",...}` |
| `devices/<THING>/telemetry` | 1 | publish | `{"thing":"...","seq":0,"img_b":12345}` |
| `devices/<THING>/image` | 0 | publish | raw JPEG bytes |
| `devices/<THING>/cmd` | — | subscribe | `{"framesize":"HD","quality":10}` |

Default `THING` = `esp32p4-device-01`

---

## File structure

```
Dockerfile.micropython          espressif/idf:v5.4 → MicroPython firmware build
Dockerfile.qemu                 Espressif QEMU + mklittlefs + runtime
Dockerfile.camera-proxy         Python/OpenCV HTTP camera server
docker-compose.yml              Reference only — not used to run containers
Makefile                        Shortcut targets (wraps docker commands)
.env.example                    Reference for environment variable names

micropython/
  boards/ESP32_P4_CAM/
    mpconfigboard.h             Enables camera module, names the board
    mpconfigboard.cmake         Sets IDF_TARGET=esp32p4, sdkconfig chain
    sdkconfig.board             360 MHz, SPIRAM Octal, MQTT buffer 8 KB
  modules/
    modcamera.c                 C module: camera.init / capture / deinit
    micropython.cmake           Links modcamera.c + esp32-camera headers
  src/
    manifest.py                 Lists boot.py + main.py to freeze into firmware
    boot.py                     WiFi connect via Secret.wifi_ssid() / Secret.wifi_password()
    main.py                     Camera capture + MQTT publish every 10 s

scripts/
  run-qemu.sh                   Emulator entrypoint: flash image, socat, QEMU
  inject-scripts.py             Uploads .py files via mpremote after QEMU boots
  setup-localstack.sh           Provisions IoT thing / policy / cert
  camera-proxy.py               HTTP server: v4l2 / network / pattern modes
  windows-camera-server.py      Windows DirectShow camera HTTP server

firmware-out/                   firmware.bin lands here after Step 7
certs/                          device.pem.crt from LocalStack after Step 8
```

---

## Bug fix log

| # | File | Bug | Fix |
|---|---|---|---|
| 1 | `micropython.cmake` | `${IDF_PATH}/../esp32-camera/` resolves incorrectly inside IDF container | Changed to `$ENV{EXTRA_COMPONENT_DIRS}/driver/include` |
| 2 | `manifest.py` | `freeze("$(PORT_DIR)/modules_frozen")` freezes `manifest.py` itself → build error | Explicitly `freeze(..., "boot.py")` and `freeze(..., "main.py")` |
| 3 | `run-qemu.sh` | `hostfwd=tcp::1883` and `hostfwd=tcp::8080` conflict with socat already bound to those ports | Removed `hostfwd`; socat relay is sufficient |
| 4 | `docker-compose.yml` | `devices: [/dev/video0]` always active → `docker compose up` fails without that device | Commented out by default |
| 5 | `sdkconfig.board` | `CONFIG_ESP32P4_DEFAULT_CPU_FREQ_MHZ=360` is wrong type for P4 Kconfig | Changed to `CONFIG_ESP32P4_DEFAULT_CPU_FREQ_360=y` |
| 6 | `sdkconfig.board` | `CONFIG_ESP32_SPIRAM_SUPPORT=y` is the original ESP32 chip key, invalid on P4 | Removed; `CONFIG_SPIRAM=y` is correct |
| 7 | `docker-compose.yml` | Bind-mounted `firmware.bin` as a file path; Docker creates a directory if absent | Mount `firmware-out/` as a directory instead |
| 8 | `Dockerfile.micropython` | Runtime stage copied `micropython.bin` which isn't always produced | Removed; only `firmware.bin` is needed |
