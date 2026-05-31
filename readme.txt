================================================================================
ESP32-P4 IoT Camera / MQTT  --  Local Development Stack
================================================================================

Target chip : ESP32-P4  (dual-core HP RISC-V @ 360 MHz, 768 KB SRAM, MIPI CSI-2)
Host        : Windows 11 + WSL2 + Docker Desktop


================================================================================
DECISION: plain docker CLI -- no docker compose
================================================================================

All instructions use plain docker commands.
docker-compose.yml is kept as a reference for the service definitions but is
NOT used to run anything.

Reasons:
  - Every step is explicit and visible -- no hidden orchestration
  - Easier to run individual services in isolation for debugging
  - No dependency on the Compose plugin version
  - Container start order, health checks, and volume creation are all
    manual and auditable


================================================================================
SERVICES
================================================================================

  Container              Image                          Ports
  ---------------------  -----------------------------  --------------------
  localstack             localstack/localstack:latest   4566, 1883, 8883
  camera-proxy           esp32p4-camera-proxy:latest    8080
  micropython-builder    esp32p4-micropython:latest     --
  esp32p4-emulator       esp32p4-emulator:latest        2323, 1234

All containers share the bridge network: iot-net


================================================================================
PREREQUISITES  --  install once
================================================================================

Docker Desktop for Windows
  Enable "Use WSL 2 based engine" in Settings > General

AWS CLI  (WSL2)
  curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
  unzip awscliv2.zip
  sudo ./aws/install

mpremote  (WSL2)
  pip install mpremote

Python + OpenCV  (Windows CMD or PowerShell -- for built-in camera)
  pip install opencv-python


================================================================================
FIRST-TIME SETUP
================================================================================

--- Step 1 -- Create secret.json ---

  cp secret.json.example secret.json

  Edit secret.json and set your real values:
    {
      "wifi_ssid":     "your-wifi-ssid",
      "wifi_password": "your-wifi-password",
      "mqtt_broker":   "192.168.1.100",
      "mqtt_port":     1883,
      "thing_name":    "esp32p4-device-01"
    }

  secret.json is listed in .gitignore -- it will never be committed.

  How secrets reach the firmware:

    All config is read via the Secret class in secret.py (frozen into firmware).

    Emulator  : run-qemu.sh reads WiFi credentials from the host's secret.json
                (mounted read-only at /secret.json) and merges them with
                emulator-specific overrides (mqtt_broker=10.0.2.2, camera
                proxy URL, emulator=true). Writes the merged secret.json into
                the virtual flash filesystem.

    Hardware  : upload-scripts uploads secret.json directly to the device
                filesystem via mpremote. secret.py reads it at runtime.

  Do not edit boot.py or main.py directly for credentials.


--- Step 2 -- Create Docker network and volume ---

  docker network create iot-net

  docker volume create localstack_data


--- Step 3 -- Build images ---

  Each image is built once. Docker layer cache makes rebuilds fast.

  camera-proxy  (~2 min)

    docker build \
      -t esp32p4-camera-proxy:latest \
      -f Dockerfile.camera-proxy \
      .

  micropython-builder  (~15-30 min)
  Pulls espressif/idf:release-v5.4, clones MicroPython v1.24.0 and
  espressif/esp32-camera, then compiles firmware.bin for ESP32-P4.

    docker build \
      -t esp32p4-micropython:latest \
      --target builder \
      --build-arg MPY_TAG=v1.24.0 \
      -f Dockerfile.micropython \
      .

  esp32p4-emulator  (~15-20 min)
  Compiles Espressif QEMU from source (esp-develop branch, riscv32-softmmu
  target with esp32p4 machine) and builds mklittlefs.

    docker build \
      -t esp32p4-emulator:latest \
      -f Dockerfile.qemu \
      .


--- Step 4 -- Start LocalStack ---

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

  Wait for the IoT service to be ready before continuing:

    until docker exec localstack \
        curl -sf http://localhost:4566/_localstack/health | grep -q '"iot"'; do
      sleep 2
    done
    echo "LocalStack ready."


--- Step 5 -- Start camera-proxy ---

  Default camera source is "network" (Windows built-in camera).
  See CAMERA MODES section to switch to v4l2 (USB) or pattern (test pattern).

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


--- Step 6 -- Start micropython-builder ---

  The container stays alive with tail -f /dev/null so you can exec into it.

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


--- Step 7 -- Copy firmware to the host ---

  firmware.bin was compiled during docker build in Step 3 and is baked into
  the image. Copy it out to ./firmware-out/ so the emulator can mount it.

    docker exec micropython-builder \
      bash -c "cp /opt/micropython/ports/esp32/build-ESP32_P4_CAM/firmware.bin \
               /firmware-out/"

    ls -lh firmware-out/firmware.bin


--- Step 8 -- Provision IoT resources on LocalStack ---

    AWS_ACCESS_KEY_ID=test \
    AWS_SECRET_ACCESS_KEY=test \
    THING_NAME=esp32p4-device-01 \
    bash scripts/setup-localstack.sh

  Creates (idempotent -- safe to re-run):
    IoT Thing   : esp32p4-device-01
    IoT Policy  : esp32p4-mqtt-policy  (connect/publish/subscribe/receive)
    Certificate : saved to ./certs/device.pem.crt


--- Step 9 -- Start the Windows camera server (built-in camera) ---

  Skip this step if using CAMERA_SOURCE=pattern.

  From Windows CMD or PowerShell:
    python scripts\windows-camera-server.py --port 8081

  Or from WSL2 (opens a new Windows CMD window):
    cmd.exe /c start "Windows Camera Server" \
      python.exe "$(wslpath -w "$(pwd)/scripts/windows-camera-server.py")" \
      --port 8081

  When Windows Firewall prompts for network access, click Allow.

  Verify: open http://localhost:8081/stream in a browser.
  You should see a live feed from the built-in camera.


--- Step 10 -- Start the emulator ---

  firmware-out/firmware.bin must exist (Step 7) before running this.

  firmware-out/firmware.bin and secret.json must both exist before running this.

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
      -e MQTT_BROKER=10.0.2.2 \
      -e MQTT_PORT=1883 \
      -e THING_NAME=esp32p4-device-01 \
      -e LOCALSTACK_HOST=localstack \
      -e CAMERA_PROXY_HOST=camera-proxy \
      -e CAMERA_PROXY_PORT=8080 \
      -e SERIAL_PORT=2323 \
      -e GDB_PORT=1234 \
      esp32p4-emulator:latest

  What run-qemu.sh does inside the container:
    1. Starts socat: 0.0.0.0:1883 -> localstack:1883   (MQTT relay)
    2. Starts socat: 0.0.0.0:8080 -> camera-proxy:8080 (camera relay)
    3. Pads firmware.bin to 8 MiB  (0xFF = erased NOR flash)
    4. Reads WiFi credentials from /secret.json (mounted from host); merges with
       emulator overrides (mqtt_broker=10.0.2.2, camera_proxy_url, emulator=true)
       and writes merged secret.json into the littlefs
    5. Copies boot.py / main.py from /scripts into the littlefs
       (secret.py is skipped -- frozen in the firmware image)
    6. Injects littlefs at flash offset 0x200000
    7. Launches: qemu-system-riscv32 -machine esp32p4
       Serial console on TCP 2323, GDB stub on TCP 1234

  Verify:
    docker logs esp32p4-emulator
    docker ps --filter name=esp32p4-emulator


--- Step 11 -- Attach to the MicroPython REPL ---

    mpremote connect socket://localhost:2323

  Press Enter if the >>> prompt does not appear immediately.
  Ctrl-X exits mpremote.

  Alternative (raw telnet):
    telnet localhost 2323


--- Step 12 -- Verify camera stream ---

  Open in browser:  http://localhost:8080/stream

  You should see a live MJPEG stream from the built-in camera.
  If CAMERA_SOURCE=pattern you see an animated color-bar test pattern.


--- Step 13 -- Verify MQTT messages ---

  Requires mosquitto_sub:
    sudo apt install mosquitto-clients

    mosquitto_sub -h localhost -p 1883 -t "devices/#" -v

  Expected every 10 seconds:
    devices/esp32p4-device-01/status     {"state":"online","chip":"esp32p4",...}
    devices/esp32p4-device-01/telemetry  {"thing":"...","seq":0,"img_b":12345}
    devices/esp32p4-device-01/image      <binary JPEG bytes>


================================================================================
DAILY WORKFLOW  (after first-time setup)
================================================================================

  # 1. Windows camera server  (Windows CMD / PowerShell)
  python scripts\windows-camera-server.py --port 8081

  # 2. Start containers  (WSL2) -- skip if already running
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


================================================================================
REBUILD FIRMWARE
================================================================================

--- Python files only (boot.py / main.py) ---

  Re-upload to the running emulator without restarting QEMU:

    docker exec esp32p4-emulator \
      inject-scripts --host localhost --port 2323 --dir /scripts


--- C code or board files (modcamera.c, sdkconfig.board, etc.) ---

  Recompile inside the running builder container:

    docker exec micropython-builder \
      bash -c "cd /opt/micropython/ports/esp32 && \
        make BOARD=ESP32_P4_CAM \
             USER_C_MODULES=modules_camera/micropython.cmake \
             FROZEN_MANIFEST=modules_frozen/manifest.py \
             -j\$(nproc)"

  Copy new firmware to host:

    docker exec micropython-builder \
      bash -c "cp /opt/micropython/ports/esp32/build-ESP32_P4_CAM/firmware.bin \
               /firmware-out/"

  Restart the emulator with the new firmware:

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
      -e MQTT_BROKER=10.0.2.2 \
      -e MQTT_PORT=1883 \
      -e THING_NAME=esp32p4-device-01 \
      -e LOCALSTACK_HOST=localstack \
      -e CAMERA_PROXY_HOST=camera-proxy \
      -e CAMERA_PROXY_PORT=8080 \
      -e SERIAL_PORT=2323 \
      -e GDB_PORT=1234 \
      esp32p4-emulator:latest


================================================================================
FLASH TO PHYSICAL ESP32-P4 HARDWARE
================================================================================

  pip install esptool

  Find serial port:
    ls /dev/ttyUSB* /dev/ttyACM*

  Erase flash:
    esptool.py --chip esp32p4 --port /dev/ttyUSB0 erase_flash

  Flash firmware:
    esptool.py --chip esp32p4 --port /dev/ttyUSB0 --baud 460800 \
      --before default_reset --after hard_reset \
      write_flash --flash_mode dio --flash_size detect 0x0 \
      firmware-out/firmware.bin

  Upload secret.json + Python scripts (secret.py is frozen in firmware):
    mpremote connect /dev/ttyUSB0 \
      cp secret.json :secret.json + \
      cp micropython/src/boot.py :boot.py + \
      cp micropython/src/main.py :main.py + \
      reset

  Serial monitor:
    mpremote connect /dev/ttyUSB0

  Before flashing, set in micropython/src/main.py:
    MQTT_BROKER = "192.168.1.100"   # your host machine LAN IP

  And in micropython/src/boot.py:
    SSID     = "your-wifi-ssid"
    PASSWORD = "your-wifi-password"


================================================================================
CAMERA MODES
================================================================================

  CAMERA_SOURCE    Camera                         Setup required
  ---------------  -----------------------------  ----------------------------
  network          Windows built-in               Run windows-camera-server.py
  (default)        (Intel IPU / DirectShow)       on Windows before Step 5
  ---------------  -----------------------------  ----------------------------
  v4l2             USB webcam via usbipd-win       See USB setup below;
                                                   add --device flag to docker run
  ---------------  -----------------------------  ----------------------------
  pattern          Animated test pattern           Nothing

--- v4l2 USB camera setup ---

  Windows PowerShell (Administrator):
    usbipd list                         # find webcam BUS-ID e.g. 2-3
    usbipd bind   --busid 2-3           # one-time per device
    usbipd attach --wsl --busid 2-3     # each Windows session

  Verify in WSL2:
    ls /dev/video*

  Replace the camera-proxy docker run command (Step 5) with:

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


================================================================================
PORT REFERENCE
================================================================================

  4566   localstack           AWS API gateway  (IoT, S3, STS)
  1883   localstack           MQTT plain
  8883   localstack           MQTT TLS
  8080   camera-proxy         GET /frame.jpg  GET /stream
  8081   windows-camera-server.py  (Windows side -- not in Docker)
  2323   esp32p4-emulator     Serial REPL  (mpremote / telnet)
  1234   esp32p4-emulator     QEMU GDB stub


================================================================================
MQTT TOPICS
================================================================================

  Topic                            QoS  Direction         Payload
  -------------------------------  ---  ----------------  ---------------------
  devices/<THING>/status           1    publish/retained  {"state":"online",...}
  devices/<THING>/telemetry        1    publish           {"seq":0,"img_b":...}
  devices/<THING>/image            0    publish           raw JPEG bytes
  devices/<THING>/cmd              --   subscribe         {"framesize":"HD",...}

  Default THING = esp32p4-device-01


================================================================================
FILE STRUCTURE
================================================================================

  Dockerfile.micropython      espressif/idf:v5.4 -> MicroPython firmware build
  Dockerfile.qemu             Espressif QEMU + mklittlefs + runtime
  Dockerfile.camera-proxy     Python/OpenCV HTTP camera server
  docker-compose.yml          Reference only -- not used to run containers
  Makefile                    Shortcut targets (wraps docker commands)
  .env.example                Reference for environment variable names

  micropython/
    boards/ESP32_P4_CAM/
      mpconfigboard.h         Enables camera module, names the board
      mpconfigboard.cmake     Sets IDF_TARGET=esp32p4, sdkconfig chain
      sdkconfig.board         360 MHz, SPIRAM Octal, MQTT buffer 8 KB
    modules/
      modcamera.c             C module: camera.init / capture / deinit
      micropython.cmake       Links modcamera.c + esp32-camera headers
    src/
      manifest.py             Lists boot.py + main.py to freeze into firmware
      boot.py                 WiFi connect on startup  (edit SSID/PASSWORD)
      main.py                 Camera capture + MQTT publish every 10 s

  scripts/
    run-qemu.sh               Emulator entrypoint: flash image, socat, QEMU
    inject-scripts.py         Uploads .py files via mpremote after QEMU boots
    setup-localstack.sh       Provisions IoT thing / policy / cert
    camera-proxy.py           HTTP server: v4l2 / network / pattern modes
    windows-camera-server.py  Windows DirectShow camera HTTP server

  firmware-out/               firmware.bin lands here after Step 7
  certs/                      device.pem.crt from LocalStack after Step 8


================================================================================
BUG FIX LOG
================================================================================

  1. micropython.cmake used ${IDF_PATH}/../esp32-camera which resolves
     incorrectly inside the IDF container.
     Fix: $ENV{EXTRA_COMPONENT_DIRS}/driver/include

  2. manifest.py used freeze("$(PORT_DIR)/modules_frozen") which includes
     manifest.py itself, causing a build error.
     Fix: explicitly freeze("...", "boot.py") and freeze("...", "main.py")

  3. run-qemu.sh passed hostfwd=tcp::1883 and hostfwd=tcp::8080 to QEMU,
     conflicting with socat already bound to those ports (EADDRINUSE).
     Fix: removed hostfwd entries; socat relay is sufficient.

  4. docker-compose.yml had devices: [/dev/video0] always active, causing
     "docker compose up" to fail on systems without that device.
     Fix: commented out by default; only enable for CAMERA_SOURCE=v4l2.

  5. sdkconfig.board set CONFIG_ESP32P4_DEFAULT_CPU_FREQ_MHZ=360 (integer)
     but ESP-IDF for P4 uses a Kconfig choice.
     Fix: CONFIG_ESP32P4_DEFAULT_CPU_FREQ_360=y

  6. sdkconfig.board included CONFIG_ESP32_SPIRAM_SUPPORT=y which is the
     original ESP32 chip key, invalid on P4.
     Fix: removed; CONFIG_SPIRAM=y is correct for P4.

  7. esp32p4-emulator bind-mounted ./firmware-out/firmware.bin as a file;
     Docker creates a directory if the path does not exist yet.
     Fix: mount ./firmware-out as a directory instead.

  8. Dockerfile.micropython runtime stage copied micropython.bin which is
     not always produced by the MicroPython build.
     Fix: removed; only firmware.bin is needed.
