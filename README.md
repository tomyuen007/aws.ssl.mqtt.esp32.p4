# ESP32-P4 IoT Camera / MQTT — Local Development Stack

**Target chip:** ESP32-P4 (dual-core HP RISC-V @ 360 MHz, 768 KB SRAM, MIPI CSI-2)  
**Host:** Windows 11 + WSL2 + Docker Desktop

---

## Current status — 2026-05-31

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
- [x] Prerequisites documented with 3 numbered steps — AWS CLI, LocalStack (Windows + WSL), LocalStack auth token
- [x] LocalStack installed on Windows (`C:\bin\localstack.exe`) and accessible from WSL bash via wrapper script at `/usr/local/bin/localstack`
- [x] `C:\bin` added to WSL `$PATH` in `~/.bashrc`
- [x] AWS CLI configured with dummy `test` credentials; `--endpoint-url http://localhost:4566` rule documented — no `awslocal` wrapper used
- [x] Manual Docker CLI steps documented for MicroPython image with per-flag explanations and `docker-compose.yml` cross-references

### Not yet done
- [ ] `LOCALSTACK_AUTH_TOKEN` added to `~/.bashrc` (Prerequisite 3)
- [ ] `secret.json` created from `secret.json.example` and filled in (Step 1)
- [ ] `docker build` for all three custom images
- [ ] LocalStack container started and IoT service verified healthy
- [ ] IoT thing / policy / certs provisioned via `setup-localstack.sh`
- [ ] MicroPython REPL via `mpremote connect socket://localhost:2323`
- [ ] Camera stream at `http://localhost:8080/stream`
- [ ] MQTT publish/subscribe verified with `mosquitto_sub`
- [ ] SSL handshake with LocalStack on port 8883 (`mqtt_ssl_verify=false`)
- [ ] Physical ESP32-P4 hardware — camera, WiFi, SSL to LocalStack and AWS IoT Core

### Resume checklist
```
-- Prerequisites (one-time) --
P1. Install AWS CLI in WSL + aws configure with test/test credentials
P2. Install LocalStack on Windows → copy to C:\bin → WSL PATH + wrapper script → localstack --version
P3. echo 'export LOCALSTACK_AUTH_TOKEN=your-token' >> ~/.bashrc && source ~/.bashrc

-- First-time setup --
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
12. python windows.camera.server\server.py --port 8081   # Windows CMD
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

## Decision: manual Docker CLI steps documented inline

Each Docker command in this project is written out with every flag explained so any developer can understand what it does without prior Docker knowledge. The `docker-compose.yml` encodes the same configuration in declarative form — use it as a cross-reference to see how a plain `docker` command maps to a Compose service definition.

---

## Manual Docker CLI — MicroPython image reference

These are the three commands needed to build the MicroPython firmware image, start a container from it, and extract the compiled `firmware.bin`. Each flag is explained so the command is self-documenting.

### 1 — Build the image

```bash
docker build \
  -t esp32p4-micropython:latest \
  --target builder \
  --build-arg MPY_TAG=v1.24.0 \
  -f Dockerfile.micropython \
  .
```

| Flag | What it does |
|---|---|
| `-t esp32p4-micropython:latest` | Names the resulting image `esp32p4-micropython` with tag `latest` |
| `--target builder` | Stops at Stage 1 (`AS builder`) — skips the slim runtime stage |
| `--build-arg MPY_TAG=v1.24.0` | Passes the MicroPython version to the `ARG MPY_TAG` in the Dockerfile |
| `-f Dockerfile.micropython` | Specifies which Dockerfile to use |
| `.` | Build context — the current directory; Docker uses this to resolve `COPY` instructions |

Cross-reference in `docker-compose.yml`: `micropython-builder.build` (lines 77–82).

### 2 — Start a container (keeps it alive for exec)

```bash
mkdir -p firmware-out

docker run -d \
  --name micropython-builder \
  --network iot-net \
  -v "$(pwd)/firmware-out:/firmware-out" \
  -e EXTRA_COMPONENT_DIRS=/opt/esp32-camera \
  --entrypoint tail \
  esp32p4-micropython:latest \
  -f /dev/null
```

| Flag | What it does |
|---|---|
| `-d` | Detached — runs in the background |
| `--name micropython-builder` | Gives the container a name so other commands can reference it |
| `--network iot-net` | Joins the shared bridge network so it can reach `localstack` and `camera-proxy` |
| `-v "$(pwd)/firmware-out:/firmware-out"` | Bind-mounts the host `firmware-out/` directory into the container at `/firmware-out` |
| `-e EXTRA_COMPONENT_DIRS=...` | Sets an environment variable the build system reads to locate `esp32-camera` |
| `--entrypoint tail` | Overrides the image's default `CMD` so the container runs `tail -f /dev/null` instead of exiting |
| `-f /dev/null` | Argument passed to `tail` — follows an empty file forever, keeping the container alive |

Cross-reference in `docker-compose.yml`: `micropython-builder` service (lines 75–93).

### 3 — Copy firmware out

```bash
docker exec micropython-builder \
  bash -c "cp /opt/micropython/ports/esp32/build-ESP32_P4_CAM/firmware.bin /firmware-out/"

ls -lh firmware-out/firmware.bin
```

| Part | What it does |
|---|---|
| `docker exec micropython-builder` | Runs a command inside the already-running container |
| `bash -c "..."` | Runs the quoted string as a shell command inside the container |
| `cp ... /firmware-out/` | Copies `firmware.bin` to the bind-mounted directory — file appears on the host immediately |

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

### Prerequisite 1 — AWS CLI (WSL2)

Install:
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
unzip awscliv2.zip
sudo ./aws/install
aws --version
```

Configure with dummy credentials for LocalStack (no real AWS account needed):
```bash
aws configure
# AWS Access Key ID:     test
# AWS Secret Access Key: test
# Default region name:   us-east-1
# Default output format: json
```

All `aws` commands must include `--endpoint-url http://localhost:4566` to target LocalStack instead of real AWS. Do not use `awslocal` or any LocalStack-specific CLI wrapper.
```bash
aws --endpoint-url http://localhost:4566 iot list-things
```

---

### Prerequisite 2 — LocalStack (Windows + WSL)

**Install LocalStack on Windows** (run in Windows CMD or PowerShell):
```cmd
pip install localstack
```

Find where pip installed `localstack.exe`:
```cmd
where localstack
```

Create `C:\bin` and copy `localstack.exe` there:
```cmd
mkdir C:\bin
copy "%LOCALAPPDATA%\Programs\Python\Python3x\Scripts\localstack.exe" C:\bin\
```
> Adjust the path to match the output of `where localstack` above.

**Make LocalStack accessible from WSL bash:**

Add `C:\bin` to the WSL `$PATH` and create a bash wrapper script so `localstack` works without `.exe`:
```bash
# Add C:\bin to PATH
echo 'export PATH="/mnt/c/bin:$PATH"' >> ~/.bashrc

# Create bash wrapper script
sudo tee /usr/local/bin/localstack > /dev/null << 'EOF'
#!/bin/bash
/mnt/c/bin/localstack.exe "$@"
EOF
sudo chmod +x /usr/local/bin/localstack

# Apply changes
source ~/.bashrc
```

Verify:
```bash
localstack --version
```

---

### Prerequisite 3 — LocalStack auth token in bash shell

Add your LocalStack auth token to `~/.bashrc` so it is available every time the terminal starts:
```bash
echo 'export LOCALSTACK_AUTH_TOKEN=your-token-here' >> ~/.bashrc
source ~/.bashrc
```

> If you are using LocalStack Community edition (free), skip this step — no token is required.

Verify the token is set:
```bash
echo $LOCALSTACK_AUTH_TOKEN
```

---

### Other tools

**Docker Desktop for Windows**
- Enable *Use WSL 2 based engine* in Settings → General

Docker socket paths by platform — no `DOCKER_HOST` needed unless `docker info` fails:

| Platform | `DOCKER_HOST` value |
|---|---|
| Windows | `npipe:///./pipe/docker_engine` |
| WSL2 | `unix:///var/run/docker.sock` |
| macOS (Docker Desktop < v4.13) | `unix:///var/run/docker.sock` |
| macOS (Docker Desktop v4.13+) | `unix://$HOME/.docker/run/docker.sock` |
| macOS (Docker Desktop v4.13+, alt) | `unix://$HOME/.docker/desktop/docker.sock` |

macOS notes:
- `/var/run/docker.sock` still exists on macOS but is a **symlink** pointing to `$HOME/.docker/run/docker.sock` — so the old path still works, it just resolves through the symlink.
- `unix://` takes exactly three slashes before the absolute path (`unix:///` + `/path`). Four slashes would mean a double-slash path (`//path`) which is non-standard.

Find the active socket on any platform:
```bash
docker context inspect | grep Host   # shows the socket the active context uses
ls -la /var/run/docker.sock          # on macOS: shows what it symlinks to
echo $DOCKER_HOST                    # shows if one is explicitly overridden
```

**mpremote (WSL2)**
```bash
pip install mpremote
```

**mosquitto-clients — for verifying MQTT (WSL2)**
```bash
sudo apt install mosquitto-clients
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
`windows.camera.server/server.py`).  See the [Camera modes](#camera-modes) section
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
python windows.camera.server\server.py --port 8081
```

**Or from WSL2** (opens a new Windows CMD window):
```bash
cmd.exe /c start "Windows Camera Server" \
  python.exe "$(wslpath -w "$(pwd)/windows.camera.server/server.py")" \
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
python windows.camera.server\server.py --port 8081

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

## Real AWS IoT Core setup

Use this section when connecting a physical ESP32-P4 to AWS IoT Core instead of LocalStack.

### One-time (shared across all devices)

**1. Get your AWS IoT endpoint:**
```bash
aws iot describe-endpoint --endpoint-type iot:Data-ATS
# output: {"endpointAddress": "<id>.iot.<region>.amazonaws.com"}
```

**2. Download the Amazon Root CA (same file for every device):**
```bash
mkdir -p certs
curl -o certs/ca.pem https://www.amazontrust.com/repository/AmazonRootCA1.pem
```

**3. Create an IoT policy (one policy can be reused by all devices):**

An IoT policy controls what an authenticated device is allowed to do.
This policy lets any ESP32 in the fleet connect and publish/subscribe on `devices/*`.

**3a. Look up your account ID and region:**
```bash
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)
echo "account=$AWS_ACCOUNT  region=$AWS_REGION"
```

**3b. Write `iot-policy.json` with your account and region substituted:**
```bash
cat > iot-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "iot:Connect",
      "Resource": "arn:aws:iot:${AWS_REGION}:${AWS_ACCOUNT}:client/\${iot:Connection.Thing.ThingName}"
    },
    {
      "Effect": "Allow",
      "Action": ["iot:Publish", "iot:Subscribe", "iot:Receive"],
      "Resource": "arn:aws:iot:${AWS_REGION}:${AWS_ACCOUNT}:topicfilter/devices/*"
    }
  ]
}
EOF
```

> The `${iot:Connection.Thing.ThingName}` variable is an AWS IoT policy variable —
> it expands at connection time to the Thing name the device uses, so each device
> can only connect with its own name. The leading `\` escapes it from shell expansion.

**3c. Create the policy:**
```bash
aws iot create-policy \
  --policy-name esp32p4-policy \
  --policy-document file://iot-policy.json
```

**3d. Verify it was created:**
```bash
aws iot get-policy --policy-name esp32p4-policy
```

Expected output includes `"policyName": "esp32p4-policy"` and the ARN.
If the policy already exists, `create-policy` returns an error — use
`aws iot create-policy-version` to update it instead.

---

### Per device

Run these steps once for each ESP32. Replace `esp32p4-device-01` with a unique name per device.

**1. Create the Thing:**
```bash
aws iot create-thing --thing-name esp32p4-device-01
```

**2. Create the device certificate and key:**
```bash
CERT_ARN=$(aws iot create-keys-and-certificate \
  --set-as-active \
  --certificate-pem-outfile certs/device.pem.crt \
  --public-key-outfile  certs/device.pub.key \
  --private-key-outfile certs/device.key \
  --query certificateArn --output text)

echo "Certificate ARN: $CERT_ARN"
```

Both `certs/device.pem.crt` and `certs/device.key` are unique to this device.
`certs/ca.pem` is the same file for every device.

**3. Attach the policy and Thing to the certificate:**
```bash
aws iot attach-policy \
  --policy-name esp32p4-policy \
  --target "$CERT_ARN"

aws iot attach-thing-principal \
  --thing-name esp32p4-device-01 \
  --principal "$CERT_ARN"
```

**4. Update `secret.json` for this device:**
```json
{
  "wifi_ssid":       "your-wifi-ssid",
  "wifi_password":   "your-wifi-password",
  "mqtt_broker":     "<id>.iot.<region>.amazonaws.com",
  "mqtt_ssl_port":   8883,
  "thing_name":      "esp32p4-device-01",
  "mqtt_ssl_verify": true,
  "ca_cert":         "ca.pem",
  "device_cert":     "device.pem.crt",
  "device_key":      "device.key"
}
```

**5. Upload certs and config to the device:**
```bash
mpremote connect /dev/ttyUSB0 \
  cp certs/ca.pem          :ca.pem          + \
  cp certs/device.pem.crt  :device.pem.crt  + \
  cp certs/device.key      :device.key      + \
  cp secret.json           :secret.json     + \
  reset
```

The device connects to AWS IoT Core on port 8883 with full mutual TLS verification.

> `certs/` is git-ignored — device keys are never committed.

---

## Fleet provisioning (many devices)

Two approaches depending on whether you pre-provision certs before shipping or let devices provision themselves on first boot.

---

### Option A — Batch script (pre-provision before shipping)

Use this when you flash each device in-house and copy its unique cert at flash time.
The script calls the same AWS CLI commands as the "Per device" steps above, in parallel.

`scripts/provision-fleet.sh` handles idempotency (skips already-provisioned devices)
and runs up to `--jobs` AWS API calls in parallel to stay within AWS IoT rate limits.

```bash
# Provision 1000 devices, 10 parallel workers
bash scripts/provision-fleet.sh --count 1000 --prefix esp32p4-device --jobs 10
```

Certs land in `certs/esp32p4-device-<NNNN>/` — one folder per device:
```
certs/
  esp32p4-device-0001/
    device.pem.crt
    device.key
    device.pub.key
  esp32p4-device-0002/
    ...
```

Flash and upload certs for a specific device (replace `0001` and port as needed):
```bash
THING=esp32p4-device-0001
PORT=/dev/ttyUSB0

# Write per-device secret.json
jq --arg t "$THING" '.thing_name = $t' secret.json > /tmp/secret-device.json

mpremote connect $PORT \
  cp certs/$THING/device.pem.crt  :device.pem.crt  + \
  cp certs/$THING/device.key      :device.key      + \
  cp certs/ca.pem                 :ca.pem          + \
  cp /tmp/secret-device.json      :secret.json     + \
  reset
```

> `certs/` is git-ignored. Back up the entire `certs/` directory securely —
> private keys cannot be re-downloaded from AWS after creation.

---

### Option B — AWS IoT Fleet Provisioning (devices self-provision on first boot)

Use this when devices ship without unique certs. Each device holds a shared
"claim certificate" burned into firmware. On first boot it connects to AWS IoT
Core with the claim cert, calls the `RegisterThing` API, and receives its own
unique cert which it stores in flash. Subsequent boots use the unique cert.

**How it works:**

```
Device boots with claim cert
        │
        ▼
Connects to AWS IoT Core (port 8883) using claim cert
        │
        ▼
Calls MQTT API: $aws/provisioning-templates/<template>/provision/json
        │
        ▼
AWS creates Thing + unique cert + attaches policy
        │
        ▼
Device receives unique cert + key over MQTT, stores to flash
        │
        ▼
Reconnects using unique cert — claim cert no longer needed
```

**Setup steps (AWS Console or CLI):**

**1. Create a provisioning template:**
```bash
cat > fleet-provisioning-template.json <<'EOF'
{
  "Parameters": {
    "ThingName": { "Type": "String" },
    "AWS::IoT::Certificate::Id": { "Type": "String" }
  },
  "Resources": {
    "thing": {
      "Type": "AWS::IoT::Thing",
      "Properties": { "ThingName": { "Ref": "ThingName" } }
    },
    "certificate": {
      "Type": "AWS::IoT::Certificate",
      "Properties": {
        "CertificateId": { "Ref": "AWS::IoT::Certificate::Id" },
        "Status": "Active"
      }
    },
    "policy": {
      "Type": "AWS::IoT::Policy",
      "Properties": { "PolicyName": "esp32p4-policy" }
    }
  }
}
EOF

aws iot create-provisioning-template \
  --template-name esp32p4-fleet \
  --template-body file://fleet-provisioning-template.json \
  --provisioning-role-arn arn:aws:iam::<account-id>:role/IoTProvisioningRole \
  --enabled
```

**2. Create claim certificates and claim policy:**

**2a. Reuse the account and region variables from step 3a (or re-export them):**
```bash
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)
```

**2b. Create the claim certificate and key:**
```bash
mkdir -p certs/claim
CLAIM_ARN=$(aws iot create-keys-and-certificate \
  --set-as-active \
  --certificate-pem-outfile certs/claim/claim.pem.crt \
  --public-key-outfile      certs/claim/claim.pub.key \
  --private-key-outfile     certs/claim/claim.key \
  --query certificateArn --output text)

echo "Claim cert ARN: $CLAIM_ARN"
```

The claim policy is intentionally more restrictive than the device policy.
It only allows connecting and publishing/subscribing to the Fleet Provisioning
MQTT topics — nothing else. Once the device has its unique cert it no longer
uses the claim cert.

**2c. Write `claim-policy.json`:**
```bash
cat > claim-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "iot:Connect",
      "Resource": "arn:aws:iot:${AWS_REGION}:${AWS_ACCOUNT}:client/*"
    },
    {
      "Effect": "Allow",
      "Action": "iot:Publish",
      "Resource": [
        "arn:aws:iot:${AWS_REGION}:${AWS_ACCOUNT}:topic/\$aws/certificates/create/json",
        "arn:aws:iot:${AWS_REGION}:${AWS_ACCOUNT}:topic/\$aws/provisioning-templates/esp32p4-fleet/provision/json"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["iot:Subscribe", "iot:Receive"],
      "Resource": [
        "arn:aws:iot:${AWS_REGION}:${AWS_ACCOUNT}:topicfilter/\$aws/certificates/create/json/accepted",
        "arn:aws:iot:${AWS_REGION}:${AWS_ACCOUNT}:topicfilter/\$aws/certificates/create/json/rejected",
        "arn:aws:iot:${AWS_REGION}:${AWS_ACCOUNT}:topicfilter/\$aws/provisioning-templates/esp32p4-fleet/provision/json/accepted",
        "arn:aws:iot:${AWS_REGION}:${AWS_ACCOUNT}:topicfilter/\$aws/provisioning-templates/esp32p4-fleet/provision/json/rejected"
      ]
    }
  ]
}
EOF
```

> The `\$aws` escapes prevent the shell from expanding `$aws` — it must arrive
> in the JSON as a literal `$aws` because that is the AWS reserved topic prefix.

**2d. Create the claim policy:**
```bash
aws iot create-policy \
  --policy-name esp32p4-claim-policy \
  --policy-document file://claim-policy.json
```

**2e. Verify it was created:**
```bash
aws iot get-policy --policy-name esp32p4-claim-policy
```

**2f. Attach the claim policy to the claim certificate:**
```bash
aws iot attach-policy \
  --policy-name esp32p4-claim-policy \
  --target "$CLAIM_ARN"
```

---

### Why the claim policy is intentionally restricted

#### Two certificates, two jobs

There are two certificates in Fleet Provisioning. They have different policies because they serve completely different purposes.

**The device policy** (`esp32p4-policy`) is attached to the unique cert a fully provisioned device receives. It allows the device to do its real job — publish telemetry, receive commands, send camera images.

**The claim policy** (`esp32p4-claim-policy`) is attached to the claim cert that is burned into firmware before shipping. Every device in the batch shares the **same** claim cert. Because it is in the firmware binary, anyone who gets hold of a physical device could potentially extract it — so it must be treated as less secret than a unique device cert.

#### What the claim policy allows vs blocks

The claim policy allows only the six MQTT topics the provisioning handshake needs:

| Topic | Direction | What it does |
|---|---|---|
| `$aws/certificates/create/json` | publish | "AWS, generate a unique cert for me" |
| `$aws/certificates/create/json/accepted` | subscribe | AWS responds with the new cert |
| `$aws/certificates/create/json/rejected` | subscribe | AWS rejects the request |
| `$aws/provisioning-templates/esp32p4-fleet/provision/json` | publish | "Register me as a Thing using this template" |
| `$aws/provisioning-templates/.../provision/json/accepted` | subscribe | AWS confirms registration |
| `$aws/provisioning-templates/.../provision/json/rejected` | subscribe | AWS rejects registration |

It **cannot** publish to `devices/*/telemetry`, subscribe to `devices/*/cmd`, or interact with any real device topic.

#### What happens if a claim cert is stolen

**With a wildcard resource policy (too permissive):**
```
Attacker uses stolen claim cert
  → can publish fake sensor data to devices/*/telemetry
  → can send commands to real devices via devices/*/cmd
  → can impersonate any device, disrupt the entire fleet
```

**With the locked-down claim policy (what we use):**
```
Attacker uses stolen claim cert
  → can only call RegisterThing and create rogue Things
  → cannot publish to any real device topic
  → cannot send commands to real devices
  → cannot read any sensor data
```

The blast radius drops from **full fleet compromise** to **provisioning spam** — and even that can be stopped.

#### Device serial number: blocking provisioning spam

"Device serial number" here does **not** mean a printed label on the box. It means a hardware-unique identifier built into the ESP32 chip itself — specifically the **chip ID**, which is the same 48-bit value as the WiFi MAC address. It is burned into hardware fuses at the factory by Espressif and cannot be changed or forged by software. It is not stored in firmware, so extracting the firmware binary does not reveal it.

When a device calls `RegisterThing` it sends a JSON payload that can include any attributes you choose. You include the chip ID as `SerialNumber`:

Read it in MicroPython:
```python
import network
chip_id = ':'.join('{:02x}'.format(b) for b in network.WLAN().config('mac'))
# e.g. "a4:cf:12:34:56:78"
```

You include this in the `RegisterThing` payload:
```json
{
  "certificateOwnershipToken": "<token from create step>",
  "parameters": {
    "SerialNumber": "a4cf12345678"
  }
}
```

Then attach a **Lambda pre-provisioning hook** to the provisioning template. AWS calls this Lambda before completing registration, passing it the `SerialNumber`. The Lambda checks the value against your manufacturing database (a DynamoDB table of chip IDs you produced and shipped). If the ID is not in the database, the Lambda returns `allowProvisioning: false` and AWS rejects the registration.

```
Device calls RegisterThing with SerialNumber=a4cf12345678
        │
        ▼
AWS calls your Lambda with the serial number
        │
        ├── ID found in manufacturing DB → allowProvisioning: true  → Thing created
        └── ID not in DB (attacker)      → allowProvisioning: false → rejected
```

This means a stolen claim cert is useless without a valid chip ID from your manufacturing run — and chip IDs are hardware-fused, not extractable from firmware alone.

---

**3. Burn claim certs into firmware:**

Copy `certs/claim/claim.pem.crt` and `certs/claim/claim.key` alongside `certs/ca.pem`
into `secret.json` as `device_cert` / `device_key` before flashing. All units in a
production batch share the same claim cert in firmware.

`main.py` must be extended to detect first boot (no unique cert in flash) and run
the Fleet Provisioning MQTT flow before starting normal operation.

> See [AWS Fleet Provisioning docs](https://docs.aws.amazon.com/iot/latest/developerguide/provision-wo-cert.html) for the full MQTT API and Python SDK example.

---

### Comparison

| | Batch script | Fleet Provisioning |
|---|---|---|
| Unique cert per device | Yes — pre-generated | Yes — generated on first boot |
| Requires in-house flashing step | Yes | No (claim cert in firmware) |
| `main.py` changes needed | No | Yes (provisioning flow on first boot) |
| Scales to large batches | Yes (parallel script) | Yes (fully automated) |
| Best for | Lab / small production runs | Mass production / OTA rollout |

---

## End-to-end fleet workflow: manufacturing to ERP

> **Visual reference:** `docs/erp-integration.pdf` — a generated PDF with colour-coded workflow diagrams covering all four phases. Regenerate with `python3 scripts/generate-erp-pdf.py`.

This section describes the complete lifecycle of a device — from the factory floor to live in your ERP system — for a fleet of 1000 units using Fleet Provisioning.

---

### Phase 1 — One-time AWS infrastructure setup (before any devices are made)

```
AWS IoT Core
  ├── IoT policy:           esp32p4-policy        (normal device operations)
  ├── IoT policy:           esp32p4-claim-policy   (provisioning only)
  ├── Provisioning template: esp32p4-fleet
  │     └── pre-provisioning Lambda hook
  └── Claim certificate:    certs/claim/claim.pem.crt + claim.key

DynamoDB
  └── Table: esp32p4-manufacturing
        PK: chip_id  (e.g. "a4cf12345678")
        Fields: batch_id, manufactured_date, firmware_version,
                provisioned (false), provisioned_at, thing_name, erp_id
```

The pre-provisioning Lambda does two things:
1. Checks `chip_id` against the DynamoDB table — rejects unknown devices
2. On success, marks `provisioned=true` and records `thing_name` in DynamoDB

---

### Phase 2 — Manufacturing (per batch, at the factory)

For each unit in the batch:

```
1. Read the chip ID from the board
     esptool.py --port /dev/ttyUSB0 chip_id
     # or in MicroPython: network.WLAN().config('mac')

2. Record the chip ID in DynamoDB
     aws dynamodb put-item \
       --table-name esp32p4-manufacturing \
       --item '{
         "chip_id":           {"S": "a4cf12345678"},
         "batch_id":          {"S": "BATCH-2026-001"},
         "manufactured_date": {"S": "2026-05-31"},
         "firmware_version":  {"S": "1.0.0"},
         "provisioned":       {"BOOL": false}
       }'

3. Flash the firmware (claim cert baked in via secret.json)
     esptool.py --chip esp32p4 --port /dev/ttyUSB0 --baud 460800 \
       write_flash 0x0 firmware-out/firmware.bin

4. Upload secret.json (contains claim cert paths, WiFi omitted — set by customer)
     mpremote connect /dev/ttyUSB0 \
       cp certs/claim/claim.pem.crt :device.pem.crt + \
       cp certs/claim/claim.key     :device.key     + \
       cp certs/ca.pem              :ca.pem         + \
       cp secret.json               :secret.json    + \
       reset

5. Box and ship
```

All 1000 units leave the factory with identical firmware. The claim cert is shared. The chip ID is what makes each unit uniquely identifiable.

---

### Phase 3 — Device first boot (in the field, fully automatic)

The customer powers on the device. Everything from here is automatic — no human intervention required.

```
Device boots
│
├── boot.py: connect to WiFi
│
├── main.py: check flash for unique cert
│     no unique cert found → enter provisioning mode
│
├── Connect to AWS IoT Core using CLAIM cert (port 8883)
│
├── Read chip ID from hardware
│     chip_id = network.WLAN().config('mac')  → "a4cf12345678"
│
├── STEP A — Request a new unique certificate
│     Publish to: $aws/certificates/create/json
│     Payload:    {} (empty)
│     AWS responds on .../accepted:
│       {
│         "certificateId":             "abc123...",
│         "certificatePem":            "-----BEGIN CERTIFICATE-----...",
│         "privateKey":                "-----BEGIN RSA PRIVATE KEY-----...",
│         "certificateOwnershipToken": "token-xyz"
│       }
│
├── STEP B — Register as a Thing
│     Publish to: $aws/provisioning-templates/esp32p4-fleet/provision/json
│     Payload:
│       {
│         "certificateOwnershipToken": "token-xyz",
│         "parameters": { "SerialNumber": "a4cf12345678" }
│       }
│
├── AWS calls pre-provisioning Lambda
│     Lambda receives: SerialNumber = "a4cf12345678"
│     Lambda queries DynamoDB → chip_id found, provisioned=false
│     Lambda updates DynamoDB: provisioned=true, provisioned_at=now,
│                              thing_name="esp32p4-a4cf12345678"
│     Lambda returns: { "allowProvisioning": true,
│                       "parameterOverrides": {
│                         "ThingName": "esp32p4-a4cf12345678" } }
│
├── AWS creates Thing "esp32p4-a4cf12345678"
│     Activates unique cert, attaches esp32p4-policy
│
├── Device receives .../provision/json/accepted
│     { "thingName": "esp32p4-a4cf12345678",
│       "deviceConfiguration": {} }
│
├── Device writes unique cert + key + thingName to flash
│     uos.rename or open('/device.pem.crt', 'w').write(certificatePem)
│     open('/device.key',      'w').write(privateKey)
│     # update secret.json: thing_name = "esp32p4-a4cf12345678"
│
├── Disconnect claim cert session
│
└── Reconnect using UNIQUE cert → normal operation begins
```

---

### Phase 4 — ERP registration (automatic, triggered on first connection)

After reconnecting with the unique cert, the device publishes a one-time registration message.

```
Device publishes to: devices/esp32p4-a4cf12345678/registered
Payload:
  {
    "thing_name":       "esp32p4-a4cf12345678",
    "chip_id":          "a4cf12345678",
    "firmware_version": "1.0.0",
    "timestamp":        1748700000
  }
```

An **AWS IoT Rule** listens on `devices/+/registered` and triggers a Lambda:

```
IoT Rule:  SELECT * FROM 'devices/+/registered'
              → Lambda: register-device-in-erp

Lambda receives the payload and calls your ERP REST API:
  POST https://erp.yourcompany.com/api/devices
  {
    "serial":    "a4cf12345678",
    "thing":     "esp32p4-a4cf12345678",
    "firmware":  "1.0.0",
    "activated": "2026-05-31T12:00:00Z"
  }

ERP creates the device record:
  - assigns internal asset ID
  - links to customer / site if pre-registered in ERP
  - sets status = "active"
  - stores thing_name for future AWS → ERP lookups

Lambda writes erp_id back to DynamoDB:
  aws dynamodb update-item \
    --table-name esp32p4-manufacturing \
    --key '{"chip_id": {"S": "a4cf12345678"}}' \
    --update-expression "SET erp_id = :id" \
    --expression-attribute-values '{":id": {"S": "ERP-00123"}}'
```

---

### Full picture

```
FACTORY                    FIELD                        CLOUD
───────                    ─────                        ─────
Flash firmware        →    Power on
Record chip_id in DB       WiFi connect
Ship device           →    First boot: no unique cert
                           Connect with claim cert   →  AWS IoT Core
                           Send chip_id              →  Lambda: validate chip_id
                                                     ←  allowProvisioning=true
                           Receive unique cert        ←  AWS creates Thing
                           Store cert to flash
                           Reconnect (unique cert)   →  AWS IoT Core
                           Publish /registered       →  IoT Rule
                                                     →  Lambda → ERP API
                                                        ERP record created
                           Normal operation          →  telemetry / images / cmds
```

---

### DynamoDB table state across the lifecycle

| Stage | `provisioned` | `provisioned_at` | `thing_name` | `erp_id` |
|---|---|---|---|---|
| Flashed at factory | `false` | — | — | — |
| First boot complete | `true` | timestamp | `esp32p4-a4cf...` | — |
| ERP registered | `true` | timestamp | `esp32p4-a4cf...` | `ERP-00123` |

---

### Idempotency: what if the device reboots mid-provisioning?

- If the device reboots before writing the unique cert to flash, it starts provisioning again from scratch. AWS will create a new cert each time — the previous incomplete cert should be cleaned up by the Lambda (deactivate certs with no attached Thing).
- If the device reboots after writing the unique cert but before publishing `/registered`, it reconnects with the unique cert and publishes `/registered` again. The ERP Lambda should be idempotent — check if `erp_id` already exists in DynamoDB before calling the ERP API.
- If the device has already provisioned (`provisioned=true` in DynamoDB), the Lambda pre-provisioning hook should return `allowProvisioning=false` to block a second provisioning attempt for the same chip ID.

---

## Camera modes

### How `windows.camera.server/server.py` fits into the project

The ESP32-P4 firmware fetches JPEG frames over HTTP and publishes them over MQTT. In the QEMU emulator there is no camera hardware, so frames come from the `camera-proxy` Docker container. But `camera-proxy` runs inside Docker on WSL2 and cannot directly access the Windows built-in camera (Intel IPU / DirectShow). `windows.camera.server/server.py` bridges this gap — it runs on **Windows** and serves frames over HTTP that Docker can reach via `host.docker.internal`.

```
Windows built-in camera (DirectShow)
        │  cv2.VideoCapture (DirectShow backend)
        ▼
windows.camera.server/server.py        Windows process, port 8081
        │  GET http://host.docker.internal:8081/frame.jpg
        ▼
camera-proxy container          Docker/WSL2, port 8080
        │  GET http://camera-proxy:8080/frame.jpg
        ▼
esp32p4-emulator (MicroPython)  QEMU, main.py fetches frame every 10 s
        │  MQTT publish  devices/<thing>/image
        ▼
localstack                      MQTT broker
```

`windows.camera.server/server.py` is only needed when `CAMERA_SOURCE=network` (the default). Switch to `CAMERA_SOURCE=v4l2` (USB webcam) or `CAMERA_SOURCE=pattern` (test pattern) and it is not required at all.

| `CAMERA_SOURCE` | Camera | Setup required |
|---|---|---|
| `network` (default) | Windows built-in (Intel IPU / DirectShow) | Run `windows.camera.server/server.py` on Windows |
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
| 8081 | windows.camera.server/server.py | Windows side — not in Docker |
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
windows.camera.server/
  server.py                     Windows DirectShow camera HTTP server (run on Windows)
  list_cameras.py               List available camera indices before starting server.py
  requirements.txt              opencv-python

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
