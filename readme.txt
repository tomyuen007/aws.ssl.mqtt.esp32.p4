================================================================================
ESP32-P4 IoT Camera / MQTT  --  Local Development Stack
================================================================================

Target chip : ESP32-P4  (dual-core HP RISC-V @ 360 MHz, 768 KB SRAM, MIPI CSI-2)
Host        : Windows 11 + WSL2 + Docker Desktop


================================================================================
PREREQUISITES  --  install once
================================================================================

--- Prerequisite 1 -- AWS CLI (WSL2) ---

  Install:
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
    unzip awscliv2.zip
    sudo ./aws/install
    aws --version

  Configure with dummy credentials for LocalStack (no real AWS account needed):
    aws configure
    # AWS Access Key ID:     test
    # AWS Secret Access Key: test
    # Default region name:   us-east-1
    # Default output format: json

  All aws commands must include --endpoint-url http://localhost:4566 to target
  LocalStack instead of real AWS. Do not use awslocal or any LocalStack-specific
  CLI wrapper.
    aws --endpoint-url http://localhost:4566 iot list-things


--- Prerequisite 2 -- LocalStack (Windows + WSL) ---

  Install LocalStack on Windows  (run in Windows CMD or PowerShell):
    pip install localstack

  Find where pip installed localstack.exe:
    where localstack

  Create C:\bin and copy localstack.exe there:
    mkdir C:\bin
    copy "%LOCALAPPDATA%\Programs\Python\Python3x\Scripts\localstack.exe" C:\bin\
  (Adjust the path to match the output of "where localstack" above.)

  Make LocalStack accessible from WSL bash:

    Add C:\bin to PATH and create a bash wrapper script so "localstack" works
    without .exe -- run these in WSL:

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

  Verify:
    localstack --version


--- Prerequisite 3 -- LocalStack auth token in bash shell ---

  Add your LocalStack auth token to ~/.bashrc so it is available every time
  the terminal starts:
    echo 'export LOCALSTACK_AUTH_TOKEN=your-token-here' >> ~/.bashrc
    source ~/.bashrc

  If you are using LocalStack Community edition (free), skip this step --
  no token is required.

  Verify the token is set:
    echo $LOCALSTACK_AUTH_TOKEN


--- Other tools ---

  Docker Desktop for Windows
    Enable "Use WSL 2 based engine" in Settings > General

    Docker socket paths by platform -- no DOCKER_HOST needed unless
    "docker info" fails:

      Platform                          DOCKER_HOST value
      --------------------------------  -----------------------------------------
      Windows                           npipe:///./pipe/docker_engine
      WSL2                              unix:///var/run/docker.sock
      macOS (Docker Desktop < v4.13)    unix:///var/run/docker.sock
      macOS (Docker Desktop v4.13+)     unix://$HOME/.docker/run/docker.sock
      macOS (Docker Desktop v4.13+alt)  unix://$HOME/.docker/desktop/docker.sock

    macOS notes:
      /var/run/docker.sock still exists on macOS but is a symlink pointing to
      $HOME/.docker/run/docker.sock -- so the old path still works, it just
      resolves through the symlink.

      unix:// takes exactly three slashes before the absolute path:
        unix:///var/run/docker.sock   <- correct (3 slashes: // + leading /)
        unix:////var/run/docker.sock  <- wrong   (4 slashes = path //var/...)

    Find the active socket on any platform:
      docker context inspect | grep Host  -- shows socket the active context uses
      ls -la /var/run/docker.sock         -- on macOS: shows what it symlinks to
      echo $DOCKER_HOST                   -- shows if one is explicitly overridden

  mpremote  (WSL2)
    pip install mpremote

  mosquitto-clients -- for verifying MQTT  (WSL2)
    sudo apt install mosquitto-clients

  Python + OpenCV  (Windows CMD or PowerShell -- for built-in camera)
    pip install opencv-python


================================================================================
CURRENT STATUS -- 2026-05-31
================================================================================

Completed
  [x] Dockerfile.micropython -- ESP-IDF v5.4 + MicroPython v1.24.0 +
      esp32-camera component; compiles firmware.bin for ESP32_P4_CAM at build
  [x] Dockerfile.qemu -- Espressif QEMU from source (esp-develop branch,
      riscv32-softmmu, esp32p4 machine) + mklittlefs
  [x] Dockerfile.camera-proxy -- Python/OpenCV HTTP server; modes: network
      (Windows built-in camera via DirectShow), v4l2 (USB via usbipd-win),
      pattern (test)
  [x] Secret class (secret.py) -- single access point for all config; reads
      secret.json from device filesystem; frozen into firmware
  [x] boot.py -- WiFi via Secret.wifi_ssid() / Secret.wifi_password()
  [x] main.py -- camera capture + MQTT publish every 10 s; SSL branch when
      emulator=false
  [x] modcamera.c -- MicroPython C module wrapping esp_camera_* for MIPI CSI-2
  [x] SSL/TLS on real hardware (port 8883); plain TCP in emulator (port 1883)
  [x] setup-localstack.sh -- provisions IoT thing/policy; saves device.pem.crt,
      device.key, ca.pem
  [x] QEMU SLiRP DNS -- emulator resolves localstack and camera-proxy by Docker
      service name via 127.0.0.11; socat relays kept as DNS-failure fallback
  [x] secret.json git-ignored; .env committed (no secrets)
  [x] All instructions use plain docker CLI -- no docker compose
  [x] GitHub repo: https://github.com/tomyuen007/aws.ssl.mqtt.esp32.p4
  [x] Prerequisites documented with 3 numbered steps -- AWS CLI, LocalStack
      (Windows + WSL), LocalStack auth token
  [x] LocalStack installed on Windows (C:\bin\localstack.exe) and accessible
      from WSL bash via wrapper script at /usr/local/bin/localstack
  [x] C:\bin added to WSL $PATH in ~/.bashrc
  [x] AWS CLI configured with dummy test credentials; --endpoint-url rule
      documented -- no awslocal wrapper used
  [x] Manual Docker CLI steps documented for MicroPython image with per-flag
      explanations and docker-compose.yml cross-references
  [x] Real AWS IoT Core setup documented -- CA cert download, IoT policy
      creation (step-by-step with account/region lookup, heredoc \$aws
      escaping explained), claim policy with locked-down Fleet Provisioning
      topics only
  [x] Fleet provisioning documented -- Option A batch script
      (provision-fleet.sh, parallel, idempotent) and Option B AWS IoT Fleet
      Provisioning with claim cert flow
  [x] windows.camera.server/ -- moved from scripts/; split into server.py,
      list_cameras.py, requirements.txt; /health endpoint enhanced with
      frame/error counts
  [x] End-to-end fleet workflow documented -- 4 phases: manufacturing ->
      first boot -> ERP registration -> normal operation; DynamoDB lifecycle
      table; idempotency handling
  [x] docs/erp-integration.pdf -- 4-page PDF with flowcharts and swim lane
      diagram; regenerate with scripts/generate-erp-pdf.py
  [x] Docker socket paths documented for WSL2, Windows, and macOS (including
      symlink note and three-slash rule)
  [x] Daily workflow, rebuild firmware, and file structure sections expanded

Not yet done
  [ ] LOCALSTACK_AUTH_TOKEN added to ~/.bashrc  (Prerequisite 3)
  [ ] secret.json created from secret.json.example and filled in  (Step 1)
  [ ] docker build for all three custom images
  [ ] LocalStack container started and IoT service verified healthy
  [ ] IoT thing / policy / certs provisioned via setup-localstack.sh
  [ ] MicroPython REPL via mpremote connect socket://localhost:2323
  [ ] Camera stream at http://localhost:8080/stream
  [ ] MQTT publish/subscribe verified with mosquitto_sub
  [ ] SSL handshake with LocalStack on port 8883 (mqtt_ssl_verify=false)
  [ ] Physical ESP32-P4 hardware -- camera, WiFi, SSL to LocalStack / AWS IoT

Resume checklist

  -- Prerequisites (one-time, WSL2) ----------------------------------------
  P1. Install AWS CLI in WSL + aws configure
        key=test, secret=test, region=us-east-1
  P2. Install LocalStack on Windows -> copy to C:\bin -> WSL PATH + wrapper
        -> localstack --version
  P3. echo 'export LOCALSTACK_AUTH_TOKEN=your-token' >> ~/.bashrc && source ~/.bashrc

  -- Prerequisites (one-time, Windows CMD) -----------------------------------
  P4. cd windows.camera.server && pip install -r requirements.txt

  -- First-time setup --------------------------------------------------------
  1.  cp secret.json.example secret.json       # fill in wifi_ssid, wifi_password
  2.  docker build -t esp32p4-camera-proxy:latest -f Dockerfile.camera-proxy .
  3.  docker build -t esp32p4-micropython:latest --target builder \
        --build-arg MPY_TAG=v1.24.0 -f Dockerfile.micropython .
  4.  docker build -t esp32p4-emulator:latest -f Dockerfile.qemu .
  5.  docker network create iot-net
  6.  docker volume create localstack_data
  7.  docker run -d --name localstack ...           # see Step 4 in readme
  8.  docker run -d --name camera-proxy ...         # see Step 5
  9.  docker run -d --name micropython-builder ...  # see Step 6
  10. docker exec micropython-builder bash -c \
        "cp .../firmware.bin /firmware-out/"        # see Step 7
  11. AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test \
        THING_NAME=esp32p4-device-01 \
        bash scripts/setup-localstack.sh            # see Step 8
  12. python windows.camera.server\server.py --port 8081   # Windows CMD
  13. docker run -d --name esp32p4-emulator ...     # see Step 10
  14. mpremote connect socket://localhost:2323
  15. mosquitto_sub -h localhost -p 1883 -t "devices/#" -v

  -- Daily workflow (after first-time setup) ---------------------------------
  A.  python windows.camera.server\server.py --port 8081   # Windows CMD
      or from WSL2: cmd.exe /c start "Camera" python.exe "$(wslpath -w ...)"
  B.  docker start localstack camera-proxy micropython-builder
  C.  until docker exec localstack curl -sf .../health | grep -q '"iot"'; do
        sleep 2; done
  D.  docker start esp32p4-emulator
  E.  mpremote connect socket://localhost:2323
  F.  docker stop esp32p4-emulator micropython-builder camera-proxy localstack

  -- Real AWS IoT Core (when ready for physical hardware) --------------------
  R1. aws iot describe-endpoint --endpoint-type iot:Data-ATS
  R2. curl -o certs/ca.pem https://www.amazontrust.com/repository/AmazonRootCA1.pem
  R3. Create iot-policy.json + aws iot create-policy   # see Real AWS IoT Core
  R4. aws iot create-thing + create-keys-and-certificate + attach
  R5. Update secret.json: mqtt_broker, mqtt_ssl_verify=true, ca_cert, certs
  R6. mpremote cp certs + secret.json to device + reset


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
DOCKER-COMPOSE.YML -- LIMITATIONS AND WHEN TO USE IT
================================================================================

  What "docker compose up" covers
  ---------------------------------
  Starts all four containers in dependency order and handles image builds,
  network/volume creation, port bindings, and env vars:

    localstack          -> waits for healthcheck (IoT service healthy)
    camera-proxy        -> starts after localstack
    micropython-builder -> starts alongside camera-proxy
    esp32p4-emulator    -> waits for localstack healthy + camera-proxy started

  What it does NOT do
  --------------------
  Missing step            Why it matters              Manual fix
  ----------------------  --------------------------  --------------------------
  Firmware copy           firmware.bin must exist     docker exec micropython-
                          before emulator starts      builder cp firmware.bin
  LocalStack provisioning No IoT Thing/policy/cert    bash scripts/
                          will exist                  setup-localstack.sh
  secret.json not mounted Emulator uses default WiFi  -v secret.json:ro
                          (HOST_SECRET not in         -e HOST_SECRET=
                          Compose file)               at docker run time
  Windows camera server   Runs on Windows -- Compose  python windows.camera.
                          cannot start it             server\server.py :8081

  Compose vs plain CLI -- side by side
  --------------------------------------
  docker compose up                  Plain docker CLI (this project)
  ---------------------------------  ----------------------------------
  Starts 4 containers automatically  Steps 4-6, 10 run manually
  depends_on handles order           Manual health-check wait loop
  Network + volume auto-created      docker network/volume create
  Image built if missing             docker build (3 separate commands)
  No firmware copy              ✗    Step 7: docker exec cp firmware.bin
  No IoT provisioning           ✗    Step 8: setup-localstack.sh
  No secret.json mount          ✗    Step 10: -v secret.json -e HOST_SECRET
  No Windows camera server      ✗    Step 9: windows.camera.server/server.py

  When to use "docker compose up"
  --------------------------------
  Use as a fast restart shortcut once the system has been set up at least once:

    # Preconditions (already done):
    #   - docker images built
    #   - firmware-out/firmware.bin exists
    #   - setup-localstack.sh has been run
    #   - secret.json exists

    # 1. Start Windows camera server (Windows CMD)
    python windows.camera.server\server.py --port 8081

    # 2. Start all containers
    docker compose up -d

    # 3. Run IoT provisioning (idempotent -- safe to re-run every time)
    AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test \
      THING_NAME=esp32p4-device-01 \
      bash scripts/setup-localstack.sh

  Note: Compose omits HOST_SECRET so the emulator falls back to default WiFi
  credentials. Use plain docker run (Step 10 in CLI guide) when real WiFi
  credentials are needed.

  Use docker-compose.yml as a cross-reference
  --------------------------------------------
  Each plain docker run command maps to a service in docker-compose.yml.
  Use it to understand what a flag does in context:

    docker run flag                        Compose equivalent
    -------------------------------------  ---------------------------
    --name localstack                      container_name: localstack
    --network iot-net                      networks: [iot-net]
    -p 4566:4566                           ports: ["4566:4566"]
    -e SERVICES=iot,sts,s3                 environment: [SERVICES=...]
    -v localstack_data:/var/lib/...        volumes: [localstack_data:...]
    --add-host host.docker.internal:...    extra_hosts: [...]


================================================================================
DECISION: manual Docker CLI steps documented inline
================================================================================

Each Docker command in this project is written out with every flag explained
so any developer can understand what it does without prior Docker knowledge.
docker-compose.yml encodes the same configuration in declarative form -- use
it as a cross-reference to see how a plain docker command maps to a Compose
service definition.


================================================================================
MANUAL DOCKER CLI -- MicroPython image reference
================================================================================

Three commands are needed to build the MicroPython firmware image, start a
container from it, and extract the compiled firmware.bin.

--- 1. Build the image ---

  docker build \
    -t esp32p4-micropython:latest \
    --target builder \
    --build-arg MPY_TAG=v1.24.0 \
    -f Dockerfile.micropython \
    .

  Flag                              What it does
  --------------------------------  --------------------------------------------
  -t esp32p4-micropython:latest     Names the image with tag latest
  --target builder                  Stops at Stage 1 (AS builder); skips slim
                                    runtime stage
  --build-arg MPY_TAG=v1.24.0       Passes MicroPython version to ARG MPY_TAG
                                    in the Dockerfile
  -f Dockerfile.micropython         Specifies which Dockerfile to use
  .                                 Build context -- current directory; Docker
                                    uses this to resolve COPY instructions

  Cross-reference in docker-compose.yml: micropython-builder.build (lines 77-82)


--- 2. Start a container (keeps it alive for exec) ---

  mkdir -p firmware-out

  docker run -d \
    --name micropython-builder \
    --network iot-net \
    -v "$(pwd)/firmware-out:/firmware-out" \
    -e EXTRA_COMPONENT_DIRS=/opt/esp32-camera \
    --entrypoint tail \
    esp32p4-micropython:latest \
    -f /dev/null

  Flag                              What it does
  --------------------------------  --------------------------------------------
  -d                                Detached -- runs in the background
  --name micropython-builder        Names the container for other commands
  --network iot-net                 Joins shared bridge network
  -v "$(pwd)/firmware-out:..."      Bind-mounts host firmware-out/ into container
  -e EXTRA_COMPONENT_DIRS=...       Env var the build system uses to find
                                    esp32-camera component
  --entrypoint tail                 Overrides the image CMD so container stays
                                    alive instead of exiting
  -f /dev/null                      Argument to tail -- follows empty file forever

  Cross-reference in docker-compose.yml: micropython-builder service (lines 75-93)


--- 3. Copy firmware out ---

  docker exec micropython-builder \
    bash -c "cp /opt/micropython/ports/esp32/build-ESP32_P4_CAM/firmware.bin \
             /firmware-out/"

  ls -lh firmware-out/firmware.bin

  Part                        What it does
  --------------------------  ------------------------------------------------
  docker exec <name>          Runs a command inside the already-running container
  bash -c "..."               Runs the quoted string as a shell command inside
                              the container
  cp ... /firmware-out/       Copies firmware.bin to the bind-mounted directory;
                              file appears on the host immediately


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
FULL CLI STARTUP GUIDE
================================================================================

  End-to-end instructions from a clean slate to a running system, CLI only.

--- Prerequisites (one-time, WSL2) ---

  P1. AWS CLI
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
    unzip awscliv2.zip && sudo ./aws/install
    aws configure
    # key=test  secret=test  region=us-east-1  output=json

  P2. LocalStack on Windows (Windows CMD):
    pip install localstack
    copy "%LOCALAPPDATA%\Programs\Python\Python3x\Scripts\localstack.exe" C:\bin\

  P3. LocalStack accessible from WSL2:
    echo 'export PATH="/mnt/c/bin:$PATH"' >> ~/.bashrc
    sudo tee /usr/local/bin/localstack > /dev/null <<'EOF'
    #!/bin/bash
    /mnt/c/bin/localstack.exe "$@"
    EOF
    sudo chmod +x /usr/local/bin/localstack
    echo 'export LOCALSTACK_AUTH_TOKEN=your-token' >> ~/.bashrc
    source ~/.bashrc

  P4. Windows camera server dependencies (Windows CMD):
    cd windows.camera.server && pip install -r requirements.txt


--- Step 1 -- Create secret.json ---

    cp secret.json.example secret.json

  Edit minimum required fields:
    python3 -c "
    import json
    s = json.load(open('secret.json'))
    s['wifi_ssid']     = 'your-ssid'
    s['wifi_password'] = 'your-password'
    json.dump(s, open('secret.json','w'), indent=2)
    "


--- Step 2 -- Create Docker network and volume ---

    docker network create iot-net
    docker volume create localstack_data


--- Step 3 -- Build all three Docker images ---

  camera-proxy (~2 min):
    docker build -t esp32p4-camera-proxy:latest -f Dockerfile.camera-proxy .

  micropython firmware builder (~15-30 min, pulls espressif/idf:release-v5.4):
    docker build \
      -t esp32p4-micropython:latest \
      --target builder \
      --build-arg MPY_TAG=v1.24.0 \
      -f Dockerfile.micropython .

  QEMU emulator (~15-20 min, compiles QEMU from source):
    docker build -t esp32p4-emulator:latest -f Dockerfile.qemu .


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

  Wait until IoT service is healthy:
    until docker exec localstack \
        curl -sf http://localhost:4566/_localstack/health | grep -q '"iot"'; do
      sleep 2
    done
    echo "LocalStack ready."

  The wait loop -- CLI or script?
  ---------------------------------
  The until block is valid bash in both forms. Paste the whole block
  directly into the terminal, or use the provided scripts:

  Multi-line script (with 120 s timeout + error message):
    bash scripts/wait.for.localstack.sh

  One-liner -- easiest to paste into a terminal:
    until docker exec localstack curl -sf http://localhost:4566/_localstack/health | grep -q '"iot"'; do sleep 2; done && echo "LocalStack ready."

  Or run the one-liner script:
    bash scripts/one.liner.wait-for-localstack.sh

  All three are equivalent. The multi-line form is for readability only --
  it is not a script requirement. When pasted as a block, bash's interactive
  mode handles the until/do/done structure and executes it at once.


--- Step 5 -- Start camera-proxy ---

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

  Use -e CAMERA_SOURCE=pattern to skip windows.camera.server entirely.


--- Step 6 -- Start micropython-builder ---

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


--- Step 7 -- Copy firmware to host ---

    docker exec micropython-builder \
      bash -c "cp /opt/micropython/ports/esp32/build-ESP32_P4_CAM/firmware.bin \
               /firmware-out/"

    ls -lh firmware-out/firmware.bin   # confirm file exists and size > 0


--- Step 8 -- Provision IoT resources on LocalStack ---

    AWS_ACCESS_KEY_ID=test \
    AWS_SECRET_ACCESS_KEY=test \
    THING_NAME=esp32p4-device-01 \
    bash scripts/setup-localstack.sh

  Expected output:
    ==> Creating IoT thing: esp32p4-device-01
    ==> Creating certificate + private key...
        device.pem.crt  saved
        device.key      saved
    Done.


--- Step 9 -- Start Windows camera server ---

  From WSL2 (no need to switch terminals):
    cmd.exe /c start "Windows Camera Server" \
      python.exe "$(wslpath -w "$(pwd)/windows.camera.server/server.py")" \
      --port 8081

  Or from Windows CMD:
    python windows.camera.server\server.py --port 8081

  Allow Windows Firewall access when prompted, then verify:
    curl -s http://host.docker.internal:8081/health
    # {"ok":true,"source":"directshow","frames":5,"errors":0}

  Skip this step if CAMERA_SOURCE=pattern was used in Step 5.


--- Step 10 -- Start the emulator ---

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

  Follow startup logs (QEMU takes 10-20 s to boot MicroPython):
    docker logs -f esp32p4-emulator
    # Expected: "MQTT -> localstack : 1883 (plain)"
    # Ctrl-C to stop following


--- Step 11 -- Verify REPL ---

    mpremote connect socket://localhost:2323
    # >>> prompt appears (press Enter if delayed)
    # >>> import sys; print(sys.version)
    # Ctrl-X to exit

  Alternative:
    telnet localhost 2323


--- Step 12 -- Verify camera stream ---

    curl -s http://localhost:8080/health
    # {"ok":true,"source":"network"}

    # Open MJPEG stream in browser (WSL2)
    explorer.exe "http://localhost:8080/stream"


--- Step 13 -- Verify MQTT messages ---

    sudo apt install mosquitto-clients   # if not installed

    mosquitto_sub -h localhost -p 1883 -t "devices/#" -v

  Expected every 10 seconds:
    devices/esp32p4-device-01/status     {"state":"online","chip":"esp32p4",...}
    devices/esp32p4-device-01/telemetry  {"thing":"...","seq":0,"img_b":12345}
    devices/esp32p4-device-01/image      <binary JPEG bytes>


--- Verify LocalStack IoT Thing ---

    aws --endpoint-url=http://localhost:4566 \
        --no-verify-ssl \
        iot list-things
    # {"things": [{"thingName": "esp32p4-device-01", ...}]}


--- Stop everything ---

    docker stop esp32p4-emulator micropython-builder camera-proxy localstack
    # Windows camera server: Ctrl-C in CMD window, or close the window


================================================================================
FIRST-TIME SETUP
================================================================================

--- Step 1 -- Create secret.json ---

  cp secret.json.example secret.json

  Edit secret.json and set your real values:
    {
      "wifi_ssid":             "your-wifi-ssid",
      "wifi_password":         "your-wifi-password",
      "mqtt_broker":           "192.168.1.100",
      "mqtt_broker_emulator":  "localstack",
      "mqtt_port":             1883,
      "mqtt_ssl_port":         8883,
      "thing_name":            "esp32p4-device-01",
      "mqtt_ssl_verify":       false,
      "ca_cert":               null,
      "device_cert":           "device.pem.crt",
      "device_key":            "device.key"
    }

  mqtt_ssl_verify and cert paths:

    Scenario          mqtt_ssl_verify  ca_cert   Notes
    ----------------  ---------------  --------  ----------------------------------
    Emulator          n/a              n/a        always plain TCP, emulator=true
    LocalStack (hw)   false            null       self-signed cert, skip verify
    Real AWS          true             "ca.pem"   use AmazonRootCA1.pem from AWS

  secret.json is listed in .gitignore -- it will never be committed.

  How secrets reach the firmware:

    All config is read via the Secret class in secret.py (frozen into firmware).

    Emulator  : run-qemu.sh reads WiFi credentials from the host's secret.json
                (mounted read-only at /secret.json) and merges them with
                emulator-specific overrides (mqtt_broker=localstack,
                camera_proxy_url=http://camera-proxy:8080/frame.jpg,
                emulator=true). Writes the merged secret.json into
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
    python windows.camera.server\server.py --port 8081

  Or from WSL2 (opens a new Windows CMD window):
    cmd.exe /c start "Windows Camera Server" \
      python.exe "$(wslpath -w "$(pwd)/windows.camera.server/server.py")" \
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
      -e MQTT_BROKER=localstack \
      -e MQTT_PORT=1883 \
      -e THING_NAME=esp32p4-device-01 \
      -e LOCALSTACK_HOST=localstack \
      -e CAMERA_PROXY_HOST=camera-proxy \
      -e CAMERA_PROXY_PORT=8080 \
      -e SERIAL_PORT=2323 \
      -e GDB_PORT=1234 \
      esp32p4-emulator:latest

  What run-qemu.sh does inside the container:
    1. Starts socat relays as DNS fallbacks (MQTT + camera -- see note below)
    2. Pads firmware.bin to 8 MiB  (0xFF = erased NOR flash)
    3. Reads WiFi credentials from /secret.json; merges with emulator overrides
       (mqtt_broker=localstack,
        camera_proxy_url=http://camera-proxy:8080/frame.jpg,
        emulator=true) and writes merged secret.json into the littlefs
    4. Copies boot.py / main.py from /scripts into the littlefs
       (secret.py is skipped -- frozen in the firmware image)
    5. Injects littlefs at flash offset 0x200000
    6. Launches: qemu-system-riscv32 -machine esp32p4
       Serial console on TCP 2323, GDB stub on TCP 1234

  Name resolution note:
    QEMU user-mode networking (SLiRP) proxies DNS through the container's
    /etc/resolv.conf -> Docker embedded DNS (127.0.0.11) -> resolves
    'localstack' and 'camera-proxy' to their iot-net IPs directly.
    The socat relays handle the rare case where DNS is not yet ready at boot.

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

  Step 1 -- Start the Windows camera server
  ------------------------------------------
  Skip if using CAMERA_SOURCE=pattern.

  From Windows CMD or PowerShell:
    python windows.camera.server\server.py --port 8081

  From WSL2 (no need to switch terminal):
    cmd.exe /c start "Windows Camera Server" \
      python.exe "$(wslpath -w "$(pwd)/windows.camera.server/server.py")" \
      --port 8081

  Verify:
    curl -s http://host.docker.internal:8081/health
    # {"ok":true,"source":"directshow","frames":N,"errors":0}


  Step 2 -- Start containers  (WSL2, skip if already running)
  ------------------------------------------------------------
    docker start localstack camera-proxy micropython-builder


  Step 3 -- Wait for LocalStack IoT to be ready
  -----------------------------------------------
    until docker exec localstack \
        curl -sf http://localhost:4566/_localstack/health | grep -q '"iot"'; do
      sleep 2
    done
    echo "LocalStack ready."


  Step 4 -- Start the emulator
  ------------------------------
    docker start esp32p4-emulator


  Step 5 -- Attach REPL
  ----------------------
    mpremote connect socket://localhost:2323

  Press Ctrl-X to exit mpremote.


  Step 6 -- Stop everything
  --------------------------
    docker stop esp32p4-emulator micropython-builder camera-proxy localstack

  The Windows camera server must be stopped with Ctrl-C in its own window.
  If launched via "cmd.exe /c start" from WSL2, close the CMD window.


================================================================================
REBUILD FIRMWARE
================================================================================

  Choose the path that matches what you changed:

    Changed                              Path
    -----------------------------------  ------------------------------------
    boot.py or main.py only              Python files -- no QEMU restart
    modcamera.c, sdkconfig.board, etc.   C code -- full recompile + restart
    secret.json only                     mpremote cp (see FLASH section)


--- Python files only (boot.py / main.py) ---

  Re-upload to the running emulator without restarting QEMU. The scripts
  directory is bind-mounted so inject-scripts picks up the latest files
  from micropython/src/:

    docker exec esp32p4-emulator \
      inject-scripts --host localhost --port 2323 --dir /scripts

  The emulator resets automatically after upload. Re-attach the REPL:

    mpremote connect socket://localhost:2323


--- C code or board files (modcamera.c, sdkconfig.board, etc.) ---

  A full recompile is needed. Stop the emulator, recompile, copy firmware,
  recreate the container.

  Step 1 -- Recompile inside the running builder container:

    docker exec micropython-builder \
      bash -c "cd /opt/micropython/ports/esp32 && \
        make BOARD=ESP32_P4_CAM \
             USER_C_MODULES=modules_camera/micropython.cmake \
             FROZEN_MANIFEST=modules_frozen/manifest.py \
             -j\$(nproc)"

  Step 2 -- Copy new firmware to host:

    docker exec micropython-builder \
      bash -c "cp /opt/micropython/ports/esp32/build-ESP32_P4_CAM/firmware.bin \
               /firmware-out/"

    ls -lh firmware-out/firmware.bin   # confirm it updated

  Step 3 -- Stop and remove the old emulator container:

    docker stop esp32p4-emulator && docker rm esp32p4-emulator

  Step 4 -- Start a new emulator container with the updated firmware:

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

  Step 5 -- Attach REPL to confirm boot:

    mpremote connect socket://localhost:2323


================================================================================
BOOT.PY
================================================================================

  Role
  ----
  boot.py is MicroPython's first user script -- the runtime executes it
  automatically before main.py every time the device boots or resets.
  Its only job is to connect to WiFi. If WiFi fails it raises OSError and
  main.py never starts.

  Frozen into firmware via manifest.py alongside secret.py and main.py.

  Boot order
  -----------
  Power on / reset
        |
        v
  MicroPython runtime initialises hardware
        |
        v
  boot.py runs  <- connects to WiFi, blocks up to 10 s
        |
        |  raises OSError if WiFi fails -> device halts here
        v
  main.py runs  <- MQTT, camera loop, etc.

  What it does
  -------------
  connect_wifi()
    |
    +-- Read SSID + password from Secret (reads secret.json once)
    +-- Activate station interface (WLAN STA_IF)
    +-- Skip connect() if already connected (safe after soft reset)
    +-- Call wlan.connect(ssid, password)
    +-- Poll wlan.isconnected() every 500 ms, up to 20 retries (10 s)
    +-- On success -> print IP address, return it
    +-- On failure -> raise OSError("WiFi connect failed")

  Why it is separate from main.py
  ---------------------------------
  MicroPython runs boot.py then main.py in sequence. Keeping WiFi setup
  in boot.py means:
    - main.py can assume the network is up -- no reconnect logic there
    - WiFi failures surface at boot before any MQTT or camera code runs
    - boot.py can be replaced independently without touching app logic

  Credentials
  ------------
  SSID and password come from Secret.wifi_ssid() / Secret.wifi_password(),
  which read secret.json. Never hard-coded in boot.py.
  See SECRET.PY section for how secret.json gets onto the device.


================================================================================
RUN-QEMU.SH
================================================================================

  Role
  ----
  run-qemu.sh is the entrypoint of the esp32p4-emulator Docker container. It
  does everything needed to boot MicroPython firmware inside QEMU and connect
  it to the Docker stack -- no manual steps after docker run.

  What it does (6 steps)
  -----------------------
  Step 1  Validate firmware.bin exists
  Step 2  Start socat MQTT relay     (0.0.0.0:1883 -> localstack:1883)
  Step 3  Start socat camera relay   (0.0.0.0:8080 -> camera-proxy:8080)
  Step 4  Build 8 MiB flash image    (pad with 0xFF, stamp firmware.bin at 0)
  Step 5  Build littlefs filesystem  (copy *.py, generate secret.json,
                                      mklittlefs)
  Step 6  Launch QEMU                (ESP32-P4, serial on TCP 2323, GDB 1234)

  Step 5 in detail -- secret.json generation
  -------------------------------------------
  run-qemu.sh generates secret.json for the emulator rather than using the
  host file directly, because the emulator needs different addresses.

  Host secret.json (mounted read-only at /secret.json)
          |
          |  read wifi_ssid, wifi_password, mqtt_broker_emulator
          v
  run-qemu.sh merges with emulator-specific overrides:
    {
      "wifi_ssid":        <from host secret.json>
      "wifi_password":    <from host secret.json>
      "mqtt_broker":      10.0.2.2    <- QEMU user-net host IP
      "mqtt_port":        1883        <- plain TCP, no SSL
      "camera_proxy_url": http://camera-proxy:8080/frame.jpg
      "emulator":         true        <- main.py skips SSL entirely
    }
          |
          v
  Written into virtual flash filesystem via mklittlefs
          |
          v
  MicroPython reads it at runtime via Secret._load()

  emulator=true is the key flag -- main.py checks it at startup and skips
  the entire SSL/TLS branch, using port 1883 with no certificate.

  Networking inside QEMU
  -----------------------
  QEMU SLiRP gives the virtual device:
    IP        10.0.2.10 (DHCP)
    Gateway   10.0.2.2  (this container)

  The firmware resolves localstack and camera-proxy by Docker DNS
  (127.0.0.11), reaching them directly. The socat relays on 0.0.0.0:1883
  and 0.0.0.0:8080 are fallbacks for connections using 10.0.2.2 directly
  (e.g. during a DNS failure):

    QEMU guest
      connects to localstack:1883 (Docker DNS)   <- primary
      or 10.0.2.2:1883 (socat relay)             <- fallback
      |
      v
    socat relay inside container -> localstack container:1883

  Environment variables
  ----------------------
  Variable            Default                       Description
  ------------------  ----------------------------  --------------------------
  FIRMWARE_BIN        /firmware/firmware.bin        Compiled MicroPython fw
  SCRIPTS_DIR         /scripts                      .py files for flash
  HOST_SECRET         /secret.json                  Host secret.json (WiFi)
  FLASH_SIZE_MB       8                             Total flash size MiB
  FS_OFFSET           0x200000                      littlefs partition start
  FS_SIZE_MB          2                             littlefs partition size
  MQTT_BROKER         10.0.2.2                      Broker in emulator secret
  MQTT_PORT           1883                          Plain TCP port
  THING_NAME          esp32p4-device-01             IoT Thing name
  LOCALSTACK_HOST     localstack                    socat MQTT relay target
  CAMERA_PROXY_HOST   camera-proxy                  socat camera relay target
  CAMERA_PROXY_PORT   8080                          Camera proxy HTTP port
  SERIAL_PORT         2323                          TCP serial console port
  GDB_PORT            1234                          QEMU GDB stub port


================================================================================
INJECT-SCRIPTS.PY
================================================================================

  Role
  ----
  inject-scripts.py is the hot-reload tool for the emulator. It uploads .py
  files into the running QEMU virtual device over the serial TCP port without
  restarting QEMU or rebuilding firmware. Installed as the inject-scripts
  command inside the esp32p4-emulator Docker image.

  Used in two ways:
    Rebuild (Python only):
      docker exec esp32p4-emulator \
        inject-scripts --host localhost --port 2323 --dir /scripts
    Makefile shortcut:
      make upload-scripts  (same docker exec command)

  What it does
  -------------
  inject-scripts --host localhost --port 2323 --dir /scripts
  |
  +-- 1. Wait for MicroPython REPL
  |        Opens TCP to localhost:2323
  |        Scans bytes for ">>>" prompt
  |        Retries every 1 s, times out after 60 s
  |
  +-- 2. Upload each .py file via mpremote
  |        For each *.py in /scripts (sorted):
  |          mpremote connect socket://localhost:2323 cp <file> :<name>
  |        Skips secret.py (frozen in firmware -- uploading would have
  |        no effect as frozen modules take priority over the filesystem)
  |        Logs each upload; prints WARNING on non-zero exit
  |
  +-- 3. Reset the device
           mpremote connect socket://localhost:2323 reset
           MicroPython reboots, runs the newly uploaded files

  Why it skips secret.py
  -----------------------
  secret.py is frozen into firmware by manifest.py. MicroPython resolves
  frozen modules before the filesystem, so uploading a secret.py to flash
  has no effect -- the frozen copy always wins.

  Relationship to run-qemu.sh
  ----------------------------
  run-qemu.sh bakes scripts into the littlefs image before QEMU starts.
  inject-scripts.py is used after QEMU is already running:

    First boot:  run-qemu.sh -> mklittlefs bakes scripts -> QEMU starts
                                                                  |
    Hot reload:  inject-scripts uploads over serial  <-----------+
                 and resets -- QEMU keeps running

  Command-line options
  ---------------------
  --host     localhost   Hostname of the serial TCP port
  --port     2323        TCP port (SERIAL_PORT in run-qemu.sh)
  --dir      /scripts    Directory of .py files to upload
  --timeout  60          Seconds to wait for REPL before giving up


================================================================================
SETUP-LOCALSTACK.SH
================================================================================

  Role
  ----
  setup-localstack.sh provisions all required AWS IoT resources on a running
  LocalStack container and saves device credentials to certs/. Run once after
  containers start -- idempotent (safe to run again if resources exist).

  Equivalent to the real-AWS per-device steps but targeting localhost:4566.

  What it does (6 steps)
  -----------------------
  Step 1  Create IoT Thing     aws iot create-thing --thing-name esp32p4-device-01
  Step 2  Create IoT Policy    allows iot:Connect/Publish/Subscribe/Receive on *
  Step 3  Create cert + key    aws iot create-keys-and-certificate --set-as-active
                               saves device.pem.crt and device.key to certs/
  Step 4  Attach policy->cert  aws iot attach-policy
  Step 5  Attach cert->Thing   aws iot attach-thing-principal
  Step 6  Extract LocalStack CA  openssl s_client -> certs/ca.pem
                               (only needed if mqtt_ssl_verify=true)

  Output files (all in certs/, git-ignored)
  ------------------------------------------
  certs/device.pem.crt   Device certificate -- upload to device flash
  certs/device.key       Device private key (chmod 600) -- upload to device flash
  certs/ca.pem           LocalStack CA cert (only if mqtt_ssl_verify=true)

  How to run it
  --------------
    AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test \
      THING_NAME=esp32p4-device-01 \
      bash scripts/setup-localstack.sh

  Dummy test credentials are required -- LocalStack accepts any value but
  the AWS CLI rejects missing credentials. --endpoint-url is baked in.

  Idempotency
  ------------
  Every AWS CLI call is followed by 2>/dev/null || echo "(already exists)".
  Running twice creates a second certificate (both valid). To start clean:
    docker rm -f localstack && docker volume rm localstack_data

  Relationship to real AWS setup
  --------------------------------
  setup-localstack.sh targets LocalStack with mqtt_ssl_verify=false.
  For real AWS use the REAL AWS IOT CORE SETUP section instead.

                  LocalStack              Real AWS
                  ----------------------  ---------------------------
  Endpoint        http://localhost:4566   aws.iot.<region>.amazonaws.com
  Credentials     test / test             Real IAM credentials
  mqtt_ssl_verify false                   true
  CA cert         certs/ca.pem            AmazonRootCA1.pem (from Amazon)
  Script          setup-localstack.sh     Manual -- see Real AWS section


================================================================================
SECRET.PY
================================================================================

  Role
  ----
  secret.py is the single access point for all runtime configuration on the
  device. Both boot.py (WiFi) and main.py (MQTT, SSL, camera URL) call
  Secret.*() methods exclusively -- neither file hard-codes credentials or
  addresses. The same firmware binary works in every environment; only
  secret.json changes.

  secret.py is frozen into the firmware at build time via manifest.py, so it
  is always present even before any files are uploaded to the device filesystem.

  How it works
  -------------
  On first access, Secret._load() opens secret.json from the device filesystem
  and caches the parsed JSON in Secret._cache. All subsequent calls read from
  the cache -- the file is opened only once per boot. If secret.json is missing
  or malformed, _cache is set to {} and every key returns its hard-coded default.

    Boot
     |
     +-- boot.py calls Secret.wifi_ssid() / Secret.wifi_password()
     |      Secret._load() opens secret.json on first call
     |      Returns cached value on subsequent calls
     |      connects to WiFi
     |
     +-- main.py calls Secret.is_emulator(), Secret.thing_name(), etc.
            uses cached values -- no second file read

  All Secret methods and what uses them
  ---------------------------------------
  Method                  Used by   Purpose
  ----------------------  --------  ------------------------------------------
  wifi_ssid()             boot.py   WiFi network name
  wifi_password()         boot.py   WiFi password
  mqtt_broker()           main.py   Broker address for real hardware
  mqtt_broker_emulator()  main.py   Broker address in QEMU (10.0.2.2 -> socat)
  mqtt_port()             main.py   Plain TCP 1883 -- emulator only
  mqtt_ssl_port()         main.py   TLS port 8883 -- real hardware only
  thing_name()            main.py   AWS IoT Thing name
  mqtt_ssl_verify()       main.py   false=LocalStack, true=real AWS
  ca_cert()               main.py   Path to CA cert PEM (null skips verify)
  device_cert()           main.py   Path to device cert PEM (mutual TLS)
  device_key()            main.py   Path to device private key PEM
  camera_proxy_url()      main.py   URL to fetch JPEG frames from
  is_emulator()           main.py   Switches TCP/TLS and selects broker address

  How secret.json gets onto the device
  --------------------------------------
  Emulator:
    run-qemu.sh generates secret.json automatically. Reads WiFi creds from
    the host secret.json (bind-mounted at /secret.json), merges emulator
    overrides (emulator=true, mqtt_broker=localstack,
    camera_proxy_url=http://camera-proxy:8080/frame.jpg, mqtt_port=1883),
    and writes the merged file into the virtual flash via mklittlefs.
    emulator=true causes main.py to skip the TLS branch entirely.

  Real hardware:
    Uploaded directly to the device filesystem with mpremote:
      mpremote connect /dev/ttyUSB0 cp secret.json :secret.json


================================================================================
MAIN.PY
================================================================================

  Role
  ----
  main.py is the application loop. It runs after boot.py has connected to
  WiFi and does three things forever:
    1. Polls MQTT for incoming commands (client.check_msg())
    2. Every 10 s: captures a frame, publishes image + telemetry
    3. Responds to devices/<thing>/cmd by reconfiguring the camera

  Frozen into firmware via manifest.py alongside boot.py and secret.py.

  Startup sequence (runs once before the main loop)
  ---------------------------------------------------
  main.py starts
  |
  +-- Read config from Secret (thing_name, emulator flag, broker, camera URL)
  |
  +-- Transport branch
  |     EMULATOR=true  -> plain TCP, port 1883, no SSL context
  |     EMULATOR=false -> TLS SSLContext
  |           mqtt_ssl_verify=false -> skip CA verification (LocalStack)
  |           mqtt_ssl_verify=true  -> load ca_cert (real AWS)
  |           device_cert + device_key present -> mutual TLS
  |
  +-- Camera branch
  |     EMULATOR=false -> camera.init() for hardware MIPI CSI-2
  |     EMULATOR=true  -> skip (no camera in QEMU)
  |
  +-- MQTT connect + subscribe to devices/<thing>/cmd
  |
  +-- Publish retained status: {"state":"online","chip":"esp32p4",...}

  Main loop (every 100 ms tick, frame every 10 s)
  -------------------------------------------------
  while True:
      client.check_msg()        <- handle any incoming cmd message

      if 10 s have elapsed:
          frame = capture_frame()  <- hardware, proxy, or stub JPEG
          publish T_IMAGE    (frame bytes, QoS 0)
          publish T_TELEMETRY ({"thing","chip","emulator","seq","img_b"}, QoS 1)

      sleep 100 ms

  Frame capture priority
  -----------------------
  1. Hardware camera (camera.capture())   -- real hardware, init succeeded
  2. HTTP proxy (_fetch_proxy_frame())    -- emulator, camera_proxy_url set
  3. Stub JPEG (1x1 grey pixel)           -- last resort, proxy unreachable

  The proxy fetch is a raw socket HTTP/1.0 GET -- no urequests dependency.

  MQTT topics
  ------------
  Topic                       Dir      QoS  Payload
  --------------------------  -------  ---  -----------------------------------
  devices/<thing>/status      publish  1    {"state","chip","emulator",
                              retained      "transport","camera"} -- on connect
  devices/<thing>/telemetry   publish  1    {"thing","chip","emulator","seq",
                                            "img_b"} -- every 10 s
  devices/<thing>/image       publish  0    Raw JPEG bytes -- every 10 s
  devices/<thing>/cmd         subscribe     {"framesize":"VGA"|"HD","quality":N}

  Transport behaviour by environment
  ------------------------------------
  emulator=true              port 1883   plain TCP   run-qemu.sh forces this
  emulator=false             port 8883   TLS         LocalStack or AWS
    mqtt_ssl_verify=false              no cert check  LocalStack self-signed
    mqtt_ssl_verify=true               CA verified    real AWS IoT Core


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
REAL AWS IOT CORE SETUP
================================================================================

  Use this section when connecting a physical ESP32-P4 to AWS IoT Core instead
  of LocalStack.

--- One-time (shared across all devices) ---

  1. Get your AWS IoT endpoint:
       aws iot describe-endpoint --endpoint-type iot:Data-ATS
       # output: {"endpointAddress": "<id>.iot.<region>.amazonaws.com"}

  2. Download Amazon Root CA (same file for every device):
       mkdir -p certs
       curl -o certs/ca.pem \
         https://www.amazontrust.com/repository/AmazonRootCA1.pem

  3. Create an IoT policy (one policy reused by all devices).

     An IoT policy controls what an authenticated device is allowed to do.
     This policy lets any ESP32 in the fleet connect and publish/subscribe
     on devices/*.

     3a. Look up your account ID and region:
           AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
           AWS_REGION=$(aws configure get region)
           echo "account=$AWS_ACCOUNT  region=$AWS_REGION"

     3b. Write iot-policy.json with your account and region substituted:
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

         ${iot:Connection.Thing.ThingName} is an AWS IoT policy variable -- it
         expands at connection time to the Thing name the device uses, so each
         device can only connect with its own name. The leading \ escapes it
         from shell expansion in the heredoc.

     3c. Create the policy:
           aws iot create-policy \
             --policy-name esp32p4-policy \
             --policy-document file://iot-policy.json

     3d. Verify it was created:
           aws iot get-policy --policy-name esp32p4-policy

         Expected output includes "policyName": "esp32p4-policy" and the ARN.
         If the policy already exists, create-policy returns an error -- use
         aws iot create-policy-version to update it instead.


--- Per device ---

  Run these steps once for each ESP32.
  Replace esp32p4-device-01 with a unique name per device.

  1. Create the Thing:
       aws iot create-thing --thing-name esp32p4-device-01

  2. Create the device certificate and key:
       CERT_ARN=$(aws iot create-keys-and-certificate \
         --set-as-active \
         --certificate-pem-outfile certs/device.pem.crt \
         --public-key-outfile      certs/device.pub.key \
         --private-key-outfile     certs/device.key \
         --query certificateArn --output text)

       echo "Certificate ARN: $CERT_ARN"

     certs/device.pem.crt and certs/device.key are unique to this device.
     certs/ca.pem is the same file for every device.

  3. Attach the policy and Thing to the certificate:
       aws iot attach-policy \
         --policy-name esp32p4-policy \
         --target "$CERT_ARN"

       aws iot attach-thing-principal \
         --thing-name esp32p4-device-01 \
         --principal "$CERT_ARN"

  4. Update secret.json for this device:
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

  5. Upload certs and config to the device:
       mpremote connect /dev/ttyUSB0 \
         cp certs/ca.pem          :ca.pem          + \
         cp certs/device.pem.crt  :device.pem.crt  + \
         cp certs/device.key      :device.key      + \
         cp secret.json           :secret.json     + \
         reset

  The device connects on port 8883 with full mutual TLS.
  certs/ is git-ignored -- device keys are never committed.


================================================================================
FLEET PROVISIONING  (many devices)
================================================================================

  Two approaches depending on whether you pre-provision certs before shipping
  or let devices self-provision on first boot.

--- Option A -- Batch script (pre-provision before shipping) ---

  Use when you flash each device in-house and copy its unique cert at flash time.

  Provision 1000 devices, 10 parallel workers:
    bash scripts/provision-fleet.sh --count 1000 --prefix esp32p4-device --jobs 10

  Certs land in certs/esp32p4-device-<NNNN>/ -- one folder per device:
    certs/
      esp32p4-device-0001/
        device.pem.crt
        device.key
        device.pub.key
      esp32p4-device-0002/
        ...

  Flash and upload certs for a specific device:
    THING=esp32p4-device-0001
    PORT=/dev/ttyUSB0

    # Write per-device secret.json (requires jq: sudo apt install jq)
    jq --arg t "$THING" '.thing_name = $t' secret.json > /tmp/secret-device.json

    mpremote connect $PORT \
      cp certs/$THING/device.pem.crt  :device.pem.crt  + \
      cp certs/$THING/device.key      :device.key      + \
      cp certs/ca.pem                 :ca.pem          + \
      cp /tmp/secret-device.json      :secret.json     + \
      reset

  Back up the entire certs/ directory securely after running the script.
  Private keys cannot be re-downloaded from AWS after creation.

  The script is idempotent -- it skips devices whose cert files already exist,
  so it is safe to re-run if interrupted partway through.


--- Option B -- AWS IoT Fleet Provisioning (devices self-provision on first boot) ---

  Use when devices ship without unique certs. Each device holds a shared
  "claim certificate" burned into firmware. On first boot it connects with the
  claim cert, calls the RegisterThing API, and receives its own unique cert
  which it stores in flash. Subsequent boots use the unique cert.

  Flow:
    Device boots with claim cert
      -> connects to AWS IoT Core (port 8883) using claim cert
      -> calls MQTT topic: $aws/provisioning-templates/<template>/provision/json
      -> AWS creates Thing + unique cert + attaches policy
      -> device receives unique cert + key over MQTT, writes to flash
      -> reconnects using unique cert (claim cert no longer needed)

  Setup:

  1. Create a provisioning template:
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

  2. Create claim certificates and claim policy.

     The claim policy is intentionally more restrictive than the device policy.
     It only allows connecting and publishing/subscribing to the Fleet
     Provisioning MQTT topics -- nothing else. Once the device has its unique
     cert it no longer uses the claim cert.

     2a. Get account ID and region:
           AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
           AWS_REGION=$(aws configure get region)

     2b. Create the claim certificate and key:
           mkdir -p certs/claim
           CLAIM_ARN=$(aws iot create-keys-and-certificate \
             --set-as-active \
             --certificate-pem-outfile certs/claim/claim.pem.crt \
             --public-key-outfile      certs/claim/claim.pub.key \
             --private-key-outfile     certs/claim/claim.key \
             --query certificateArn --output text)

           echo "Claim cert ARN: $CLAIM_ARN"

     2c. Write claim-policy.json:
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

         \$aws escapes prevent the shell from expanding $aws -- it must arrive
         in the JSON as a literal $aws (the AWS reserved topic prefix).

     2d. Create the claim policy:
           aws iot create-policy \
             --policy-name esp32p4-claim-policy \
             --policy-document file://claim-policy.json

     2e. Verify it was created:
           aws iot get-policy --policy-name esp32p4-claim-policy

     2f. Attach the claim policy to the claim certificate:
           aws iot attach-policy \
             --policy-name esp32p4-claim-policy \
             --target "$CLAIM_ARN"

  -- Why the claim policy is intentionally restricted --

  Two certificates, two jobs
  --------------------------
  There are two certificates in Fleet Provisioning. They have different
  policies because they serve completely different purposes.

  The device policy (esp32p4-policy) is attached to the unique cert a fully
  provisioned device receives. It allows the device to do its real job --
  publish telemetry, receive commands, send camera images.

  The claim policy (esp32p4-claim-policy) is attached to the claim cert
  burned into firmware before shipping. Every device in the batch shares the
  SAME claim cert. Because it is in the firmware binary, anyone who gets hold
  of a physical device could potentially extract it -- so it must be treated
  as less secret than a unique device cert.

  What the claim policy allows vs blocks
  ---------------------------------------
  The claim policy allows only the six MQTT topics the provisioning handshake
  needs:

    Topic                                                   Direction  Purpose
    ------------------------------------------------------  ---------  -------
    $aws/certificates/create/json                           publish    Request a new unique cert
    $aws/certificates/create/json/accepted                  subscribe  AWS returns the new cert
    $aws/certificates/create/json/rejected                  subscribe  AWS rejects the request
    $aws/provisioning-templates/esp32p4-fleet/provision/json publish   Register as a Thing
    .../provision/json/accepted                             subscribe  AWS confirms registration
    .../provision/json/rejected                             subscribe  AWS rejects registration

  It cannot publish to devices/*/telemetry, subscribe to devices/*/cmd, or
  interact with any real device topic.

  What happens if a claim cert is stolen
  ---------------------------------------
  With a wildcard resource policy (too permissive):
    Attacker uses stolen claim cert
      -> can publish fake sensor data to devices/*/telemetry
      -> can send commands to real devices via devices/*/cmd
      -> can impersonate any device, disrupt the entire fleet

  With the locked-down claim policy (what we use):
    Attacker uses stolen claim cert
      -> can only call RegisterThing and create rogue Things
      -> cannot publish to any real device topic
      -> cannot send commands to real devices
      -> cannot read any sensor data

  The blast radius drops from full fleet compromise to provisioning spam --
  and even that can be stopped.

  Device serial number: blocking provisioning spam
  ------------------------------------------------
  "Device serial number" here does NOT mean a printed label on the box. It
  means a hardware-unique identifier built into the ESP32 chip itself --
  specifically the chip ID, which is the same 48-bit value as the WiFi MAC
  address. It is burned into hardware fuses at the factory by Espressif and
  cannot be changed or forged by software. It is not stored in firmware, so
  extracting the firmware binary does not reveal it.

  When a device calls RegisterThing it sends a JSON payload that can include
  any attributes you choose. You include the chip ID as SerialNumber:

  Read it in MicroPython:
    import network
    chip_id = ':'.join('{:02x}'.format(b) for b in network.WLAN().config('mac'))
    # e.g. "a4:cf:12:34:56:78"

  Include it in the RegisterThing payload:
    {
      "certificateOwnershipToken": "<token from create step>",
      "parameters": {
        "SerialNumber": "a4cf12345678"
      }
    }

  Then attach a Lambda pre-provisioning hook to the provisioning template.
  AWS calls this Lambda before completing registration, passing it the
  SerialNumber. The Lambda checks the value against your manufacturing
  database (a DynamoDB table of chip IDs you produced and shipped). If the
  ID is not in the database, the Lambda returns allowProvisioning=false and
  AWS rejects the registration.

    Device calls RegisterThing with SerialNumber=a4cf12345678
            |
            v
    AWS calls your Lambda with the serial number
            |
            +-- ID found in manufacturing DB -> allowProvisioning=true  -> Thing created
            +-- ID not in DB (attacker)      -> allowProvisioning=false -> rejected

  A stolen claim cert is useless without a valid chip ID from your
  manufacturing run -- and chip IDs are hardware-fused, not extractable from
  firmware alone.


  3. Burn claim certs into firmware:
     Copy certs/claim/claim.pem.crt and certs/claim/claim.key alongside
     certs/ca.pem into secret.json as device_cert / device_key before flashing.
     All units in a production batch share the same claim cert.

     main.py must be extended to detect first boot (no unique cert in flash)
     and run the Fleet Provisioning MQTT flow before starting normal operation.

     See: https://docs.aws.amazon.com/iot/latest/developerguide/provision-wo-cert.html


--- Comparison ---

  Approach            Unique cert/device  In-house flash step  main.py changes  Best for
  ------------------  ------------------  -------------------  ---------------  --------
  Batch script        Yes (pre-generated) Required             No               Lab / small runs
  Fleet Provisioning  Yes (on first boot) Not required         Yes              Mass production


================================================================================
END-TO-END FLEET WORKFLOW: MANUFACTURING TO ERP
================================================================================

  Visual reference: docs/erp-integration.pdf
    Colour-coded workflow diagrams covering all four phases.
    Regenerate with: python3 scripts/generate-erp-pdf.py

  Complete lifecycle for 1000 devices using Fleet Provisioning -- from factory
  floor to live in your ERP system.

--- Phase 1 -- One-time AWS infrastructure setup (before any devices are made) ---

  AWS IoT Core
    esp32p4-policy          -- normal device operations
    esp32p4-claim-policy    -- provisioning topics only
    esp32p4-fleet template  -- with pre-provisioning Lambda hook
    Claim certificate       -- certs/claim/claim.pem.crt + claim.key

  DynamoDB table: esp32p4-manufacturing
    PK: chip_id  (e.g. "a4cf12345678")
    Fields:
      batch_id          e.g. "BATCH-2026-001"
      manufactured_date e.g. "2026-05-31"
      firmware_version  e.g. "1.0.0"
      provisioned       false (updated to true on first boot)
      provisioned_at    timestamp (set on first boot)
      thing_name        set on first boot
      erp_id            set after ERP registration

  Pre-provisioning Lambda does two things:
    1. Checks chip_id against DynamoDB -- rejects unknown devices
    2. On success, marks provisioned=true and records thing_name


--- Phase 2 -- Manufacturing (per batch, at the factory) ---

  For each of the 1000 units:

  1. Read chip ID from the board:
       esptool.py --port /dev/ttyUSB0 chip_id
       # or later in MicroPython: network.WLAN().config('mac')

  2. Record chip ID in DynamoDB:
       aws dynamodb put-item \
         --table-name esp32p4-manufacturing \
         --item '{
           "chip_id":           {"S": "a4cf12345678"},
           "batch_id":          {"S": "BATCH-2026-001"},
           "manufactured_date": {"S": "2026-05-31"},
           "firmware_version":  {"S": "1.0.0"},
           "provisioned":       {"BOOL": false}
         }'

  3. Flash firmware (claim cert baked in via secret.json):
       esptool.py --chip esp32p4 --port /dev/ttyUSB0 --baud 460800 \
         write_flash 0x0 firmware-out/firmware.bin

  4. Upload claim cert + config:
       mpremote connect /dev/ttyUSB0 \
         cp certs/claim/claim.pem.crt :device.pem.crt + \
         cp certs/claim/claim.key     :device.key     + \
         cp certs/ca.pem              :ca.pem         + \
         cp secret.json               :secret.json    + \
         reset

  5. Box and ship.

  All 1000 units leave the factory with identical firmware and the same claim
  cert. The chip ID is what makes each unit uniquely identifiable.


--- Phase 3 -- Device first boot (in the field, fully automatic) ---

  Customer powers on the device. Everything from here is automatic.

  Device boots
  |
  +-- boot.py: connect to WiFi
  |
  +-- main.py: check flash for unique cert
  |     no unique cert found -> enter provisioning mode
  |
  +-- Connect to AWS IoT Core using CLAIM cert (port 8883)
  |
  +-- Read chip ID from hardware
  |     chip_id = network.WLAN().config('mac')  -> "a4cf12345678"
  |
  +-- STEP A: Request a new unique certificate
  |     Publish to: $aws/certificates/create/json
  |     Payload:    {}  (empty)
  |     AWS responds on .../accepted:
  |       {
  |         "certificateId":             "abc123...",
  |         "certificatePem":            "-----BEGIN CERTIFICATE-----...",
  |         "privateKey":                "-----BEGIN RSA PRIVATE KEY-----...",
  |         "certificateOwnershipToken": "token-xyz"
  |       }
  |
  +-- STEP B: Register as a Thing
  |     Publish to: $aws/provisioning-templates/esp32p4-fleet/provision/json
  |     Payload:
  |       {
  |         "certificateOwnershipToken": "token-xyz",
  |         "parameters": { "SerialNumber": "a4cf12345678" }
  |       }
  |
  +-- AWS calls pre-provisioning Lambda
  |     Lambda receives: SerialNumber = "a4cf12345678"
  |     Lambda queries DynamoDB -> chip_id found, provisioned=false
  |     Lambda updates DynamoDB:
  |       provisioned=true, provisioned_at=now,
  |       thing_name="esp32p4-a4cf12345678"
  |     Lambda returns:
  |       { "allowProvisioning": true,
  |         "parameterOverrides": { "ThingName": "esp32p4-a4cf12345678" } }
  |
  +-- AWS creates Thing "esp32p4-a4cf12345678"
  |     Activates unique cert, attaches esp32p4-policy
  |
  +-- Device receives .../provision/json/accepted
  |     { "thingName": "esp32p4-a4cf12345678" }
  |
  +-- Device writes unique cert + key + thingName to flash
  |
  +-- Disconnect claim cert session
  |
  +-- Reconnect using UNIQUE cert -> normal operation begins


--- Phase 4 -- ERP registration (automatic, triggered on first connection) ---

  After reconnecting with the unique cert, device publishes a one-time
  registration message:

    Topic:   devices/esp32p4-a4cf12345678/registered
    Payload:
      {
        "thing_name":       "esp32p4-a4cf12345678",
        "chip_id":          "a4cf12345678",
        "firmware_version": "1.0.0",
        "timestamp":        1748700000
      }

  An AWS IoT Rule listens on devices/+/registered and triggers a Lambda:

    IoT Rule: SELECT * FROM 'devices/+/registered'
                -> Lambda: register-device-in-erp

    Lambda calls your ERP REST API:
      POST https://erp.yourcompany.com/api/devices
      {
        "serial":    "a4cf12345678",
        "thing":     "esp32p4-a4cf12345678",
        "firmware":  "1.0.0",
        "activated": "2026-05-31T12:00:00Z"
      }

    ERP creates the device record:
      - assigns internal asset ID
      - links to customer / site if pre-registered
      - sets status = "active"
      - stores thing_name for future AWS->ERP lookups

    Lambda writes erp_id back to DynamoDB:
      aws dynamodb update-item \
        --table-name esp32p4-manufacturing \
        --key '{"chip_id": {"S": "a4cf12345678"}}' \
        --update-expression "SET erp_id = :id" \
        --expression-attribute-values '{":id": {"S": "ERP-00123"}}'


--- Full picture ---

  FACTORY                    FIELD                       CLOUD
  -------                    -----                       -----
  Flash firmware        ->   Power on
  Record chip_id in DB       WiFi connect
  Ship device           ->   First boot: no unique cert
                             Connect with claim cert  -> AWS IoT Core
                             Send chip_id             -> Lambda: validate
                                                      <- allowProvisioning=true
                             Receive unique cert       <- AWS creates Thing
                             Store cert to flash
                             Reconnect (unique cert)  -> AWS IoT Core
                             Publish /registered      -> IoT Rule
                                                      -> Lambda -> ERP API
                                                         ERP record created
                             Normal operation         -> telemetry/images/cmds


--- DynamoDB table state across the lifecycle ---

  Stage                  provisioned  provisioned_at  thing_name         erp_id
  ---------------------  -----------  --------------  -----------------  -------
  Flashed at factory     false        --              --                 --
  First boot complete    true         timestamp       esp32p4-a4cf...    --
  ERP registered         true         timestamp       esp32p4-a4cf...    ERP-00123


--- Idempotency: what if the device reboots mid-provisioning? ---

  Before unique cert is written to flash:
    Device starts provisioning again. AWS issues a new cert each time.
    The Lambda should deactivate incomplete certs (no attached Thing).

  After unique cert written but before /registered published:
    Device reconnects with unique cert and republishes /registered.
    The ERP Lambda must be idempotent -- check erp_id in DynamoDB before
    calling the ERP API to avoid creating duplicate records.

  If device tries to provision again after provisioned=true:
    The Lambda returns allowProvisioning=false, blocking a second attempt
    for the same chip_id. Only one unique cert is ever issued per device.


================================================================================
WINDOWS.CAMERA.SERVER
================================================================================

  Standalone Windows-side camera server. Captures the built-in camera via
  DirectShow and serves JPEG frames over HTTP for the Docker camera-proxy.

--- Folder structure ---

  windows.camera.server/
    server.py           Main HTTP server -- captures camera, serves endpoints
    list_cameras.py     Utility to probe available DirectShow camera indices
    requirements.txt    opencv-python

--- One-time setup ---

  Run once from Windows CMD or PowerShell (NOT WSL):
    cd windows.camera.server
    pip install -r requirements.txt

--- Find available camera indices ---

  If you have multiple cameras or index 0 does not work:
    python windows.camera.server\list_cameras.py

  Example output:
    Scanning camera indices 0-4 (DirectShow) ...

      [0]  640x480  -- readable
      [1]  not available

    Use --index 0 with server.py
    Example:  python server.py --index 0 --port 8081

--- Run the server ---

  From Windows CMD or PowerShell:
    python windows.camera.server\server.py --port 8081

  From WSL2 (without switching to a Windows terminal):
    cmd.exe /c start "Windows Camera Server" \
      python.exe "$(wslpath -w "$(pwd)/windows.camera.server/server.py")" \
      --port 8081

  When Windows Firewall prompts, click Allow.

--- Command-line options ---

  Option      Default  Description
  ----------  -------  ------------------------------------------------
  --index     0        DirectShow camera index (use list_cameras.py first)
  --port      8081     HTTP port the server listens on
  --width     640      Capture width in pixels
  --height    480      Capture height in pixels
  --quality   85       JPEG quality 1-100

--- Endpoints ---

  GET /frame.jpg   Latest JPEG frame (what camera-proxy polls every ~33 ms)
  GET /stream      MJPEG stream (open in browser for live preview)
  GET /health      JSON: {"ok":true,"source":"directshow","frames":N,"errors":N}

--- Verify it is working ---

  From a browser on any machine on the same network:
    http://localhost:8081/stream

  From WSL2 or Docker (via host.docker.internal):
    curl -s http://host.docker.internal:8081/health
    # {"ok":true,"source":"directshow","frames":142,"errors":0}


================================================================================
CAMERA.PROXY
================================================================================

  Role
  ----
  camera.proxy is the Docker container package that provides camera frames to
  the emulated ESP32-P4. server.py is the container entrypoint -- it runs
  inside the camera-proxy container on WSL2, starts a capture backend, and
  serves frames over HTTP. MicroPython main.py fetches
  http://camera-proxy:8080/frame.jpg every 10 s and publishes the JPEG bytes
  as an MQTT image message.

  Middle layer: MicroPython always talks to the same URL regardless of whether
  the real source is the Windows camera, USB webcam, or test pattern.

  Folder structure
  -----------------
  camera.proxy/
    server.py           Docker entrypoint -- env vars, backend start, HTTP server
    list_cameras.py     Probe /dev/videoN; run to find CAMERA_DEVICE index
    requirements.txt    opencv-python-headless, numpy
    backends/
      __init__.py       start() -- maps CAMERA_SOURCE to the right backend
      v4l2.py           V4L2 capture ~30 fps; falls back to pattern on error
      network.py        Polls windows.camera.server at 10 fps; pattern fallback
      pattern.py        NumPy colour-bar; generate() shared by other backends

  Where it sits in the full chain
  --------------------------------
  Windows camera (DirectShow)
          | windows.camera.server/server.py  (Windows, port 8081)
          | GET http://host.docker.internal:8081/frame.jpg
          v
  camera-proxy container  <- camera.proxy/server.py  (port 8080)
          |   backends/network.py  polls windows.camera.server
          |   backends/v4l2.py     reads /dev/video0
          |   backends/pattern.py  generates test frames
          | GET http://camera-proxy:8080/frame.jpg
          v
  esp32p4-emulator  (MicroPython main.py, every 10 s)
          | MQTT publish  devices/<thing>/image
          v
  localstack  (MQTT broker)

  How server.py works
  --------------------
  Container starts -> python3 /app/server.py
        |
        +-- Read env vars (CAMERA_SOURCE, CAMERA_URL, CAMERA_DEVICE, ...)
        +-- backends.start(SOURCE, state, ...)
        |     starts one daemon capture thread
        |     thread writes latest JPEG into shared state["jpeg"] (lock)
        +-- time.sleep(0.15)  <- wait for first frame
        +-- HTTPServer("0.0.0.0", PORT).serve_forever()
                  |
                  +-- GET /frame.jpg  read state["jpeg"], return image/jpeg
                  +-- GET /stream     MJPEG multipart loop
                  +-- GET /health     {"ok":true,"source":"..."}

  The backends
  -------------
  Backend   File                  Behaviour
  --------  --------------------  --------------------------------------------
  network   backends/network.py   Polls CAMERA_URL every 100 ms; falls back
                                  to pattern.generate() on error; warns every
                                  30 consecutive failures
  v4l2      backends/v4l2.py      Opens /dev/video0 via OpenCV V4L2; ~30 fps;
                                  falls back to pattern.generate() on read err
  pattern   backends/pattern.py   NumPy colour-bar + scan line + frame counter
  auto      backends/__init__.py  Tries v4l2 first; falls back to pattern

  pattern.py exports generate(n, width, height) so v4l2.py and network.py
  can produce a test frame during fallback without duplicating drawing code.

  list_cameras.py
  ----------------
  Run to find available V4L2 device indices before setting CAMERA_DEVICE:
    docker exec camera-proxy python3 /app/list_cameras.py
    # or on WSL2 host:
    python3 camera.proxy/list_cameras.py

  Endpoints
  ----------
  GET /frame.jpg   Latest JPEG -- MicroPython fetches this every 10 s
  GET /stream      MJPEG multipart stream ~10 fps (open in browser)
  GET /health      {"ok":true,"source":"network"|"v4l2"|"pattern"}

  Environment variables
  ----------------------
  CAMERA_SOURCE    auto      network / v4l2 / pattern / auto
  CAMERA_URL       http://host.docker.internal:8081/frame.jpg
  CAMERA_DEVICE    0         V4L2 device index (use list_cameras.py to find)
  CAMERA_WIDTH     640       Capture / pattern width
  CAMERA_HEIGHT    480       Capture / pattern height
  JPEG_QUALITY     85        JPEG encode quality 1-100
  PORT             8080      HTTP port


================================================================================
DOCKERFILE.CAMERA-PROXY
================================================================================

  Role
  ----
  Dockerfile.camera-proxy builds the esp32p4-camera-proxy:latest image --
  the Docker image that runs the camera-proxy container. It packages the
  entire camera.proxy/ Python package into a lightweight Python 3.12
  container with OpenCV and V4L2 support.

  Build command
  --------------
    docker build -t esp32p4-camera-proxy:latest -f Dockerfile.camera-proxy .

  Build context is the repo root so COPY instructions can reach camera.proxy/.

  What the build does (layer by layer)
  --------------------------------------
  FROM python:3.12-slim
        |
        +-- apt-get install libgl1 libglib2.0-0 libv4l-dev v4l-utils
        |     libgl1 / libglib2.0-0  -> opencv-python-headless runtime deps
        |     libv4l-dev / v4l-utils -> V4L2 kernel interface for /dev/video0
        |
        +-- COPY camera.proxy/requirements.txt -> pip install
        |     opencv-python-headless  (no GUI -- smaller than full opencv)
        |     numpy
        |     Separate COPY so Docker caches the pip layer; only re-runs
        |     pip when requirements.txt changes, not on every source edit
        |
        +-- COPY camera.proxy/ /app/
        |     server.py, list_cameras.py, backends/__init__.py, backends/*.py
        |
        +-- ENV  CAMERA_SOURCE=auto  CAMERA_URL=...  CAMERA_DEVICE=0  ...
        |     Default env vars -- all overridable at docker run with -e
        |
        +-- CMD ["python3", "/app/server.py"]
              Container entrypoint -- server.py runs in the foreground

  Why opencv-python-headless not opencv-python
  ---------------------------------------------
  opencv-python includes GUI window support (GTK/Qt) which pulls in large
  display libraries. The container has no display and never opens a window.
  opencv-python-headless provides the same V4L2 and image encoding at a
  smaller image size.

  Why requirements.txt is copied separately before the source
  ------------------------------------------------------------
    COPY camera.proxy/requirements.txt /app/requirements.txt  <- layer A
    RUN  pip install -r /app/requirements.txt                 <- layer B (cached)
    COPY camera.proxy/ /app/                                  <- layer C

  Layer B (pip install) only re-runs if layer A changes -- i.e. if
  requirements.txt changes. Editing server.py or a backend only invalidates
  layer C, not the slow pip layer. Iterative rebuilds stay fast.

  Image contents at runtime
  --------------------------
  /app/
    server.py
    list_cameras.py
    requirements.txt
    backends/
      __init__.py
      v4l2.py
      network.py
      pattern.py

  A single Python process: one HTTP thread + one capture daemon thread.
  No shell, no process manager.


================================================================================
DOCKERFILE.QEMU
================================================================================

  Role
  ----
  Dockerfile.qemu builds the esp32p4-emulator:latest image -- the Docker
  image that runs the QEMU ESP32-P4 emulator. Three-stage build: two builder
  stages compile QEMU and mklittlefs from source; a slim runtime stage
  assembles the final image using only the compiled binaries.

  Build command
  --------------
    docker build -t esp32p4-emulator:latest -f Dockerfile.qemu .

  ~15-20 min on first build. Docker cache makes rebuilds instant.

  What the build does (three stages)
  ------------------------------------
  Stage 1 -- qemu-builder  (ubuntu:24.04)
        |
        +-- apt: gcc/cmake/ninja/pkg-config + libglib/pixman/fdt/slirp dev
        |
        +-- git clone --depth 1 --branch esp-develop
        |     https://github.com/espressif/qemu.git
        |     (Espressif fork -- adds ESP32-P4 to riscv32-softmmu)
        |
        +-- ./configure --target-list=riscv32-softmmu
        |               --enable-slirp  (SLiRP user-mode networking)
        |               --disable-docs/gtk/sdl/opengl/user
        +-- make -j$(nproc) && make install -> /opt/qemu/

  Stage 2 -- lfs-builder  (ubuntu:24.04)
        |
        +-- apt: build-essential git cmake
        +-- git clone mklittlefs (with submodules)
        +-- make dist -> /opt/mklittlefs/mklittlefs

  Stage 3 -- runtime  (ubuntu:24.04, final image)
        |
        +-- apt: libglib2.0-0 libpixman-1-0 libfdt1 libslirp0
        |         socat python3 python3-pip
        +-- pip: mpremote esptool
        +-- COPY qemu-system-riscv32  -> /usr/local/bin/
        +-- COPY share/qemu/          -> /usr/local/share/qemu/
        +-- COPY mklittlefs           -> /usr/local/bin/
        +-- COPY run-qemu.sh          -> /usr/local/bin/run-qemu
        +-- COPY inject-scripts.py    -> /usr/local/bin/inject-scripts
        +-- VOLUME ["/firmware", "/scripts"]
        +-- EXPOSE 2323  (serial console TCP)
        +-- EXPOSE 1234  (GDB stub TCP)
        +-- ENTRYPOINT ["run-qemu"]

  Why Espressif's QEMU fork
  --------------------------
  Upstream QEMU does not support the ESP32-P4. Espressif maintains a fork
  that adds the esp32p4 machine type to riscv32-softmmu. The esp-develop
  branch is the active maintenance branch.

  Why three stages
  -----------------
  Builder stages need the full compiler toolchain (~500 MB). The runtime
  image only needs compiled binaries + shared library deps (~80 MB).
  Multi-stage build discards the toolchain entirely.

  Key tools in the runtime image
  --------------------------------
  qemu-system-riscv32   Stage 1   Runs the ESP32-P4 virtual machine
  mklittlefs            Stage 2   Packs scripts + secret.json into littlefs
  socat                 apt       MQTT and camera DNS-fallback relays
  mpremote              pip       Upload .py files over TCP serial
  esptool               pip       Available for flash operations
  run-qemu              COPY      Container entrypoint (run-qemu.sh)
  inject-scripts        COPY      Hot-reload tool (inject-scripts.py)

  Bind-mount volumes
  -------------------
  /firmware  <- firmware-out/ (host)      firmware.bin from micropython-builder
  /scripts   <- micropython/src/ (host)   boot.py, main.py (secret.py skipped)

  /secret.json is a third bind mount added at docker run time (single file,
  not declared as VOLUME).


================================================================================
CONTAINER FILE INVENTORY
================================================================================

  Files present inside each running container -- baked-in vs bind-mounted.

--- localstack (official image -- no custom Dockerfile) ---

  /var/lib/localstack/     <- bind-mounted from localstack_data volume
  /var/run/docker.sock     <- bind-mounted from host (Docker access)

--- camera-proxy ---

  Built from Dockerfile.camera-proxy. All source files baked in under /app/:

  /app/
    server.py              <- HTTP server entrypoint (CMD)
    list_cameras.py        <- V4L2 camera probe utility
    requirements.txt
    backends/
      __init__.py          <- backend selection (CAMERA_SOURCE -> start())
      v4l2.py              <- V4L2 capture loop
      network.py           <- network fetch loop
      pattern.py           <- NumPy test pattern generator

  No bind mounts -- all files are COPY'd into the image at build time.

--- micropython-builder ---

  Built from Dockerfile.micropython (builder stage).

  /opt/micropython/
    ports/esp32/
      boards/ESP32_P4_CAM/          <- COPY'd from micropython/boards/ESP32_P4_CAM/
        mpconfigboard.h
        mpconfigboard.cmake
        sdkconfig.board
      modules_camera/               <- COPY'd from micropython/modules/
        micropython.cmake
        modcamera.c
      modules_frozen/               <- COPY'd from micropython/src/ + overridden by bind mount
        manifest.py
        boot.py
        main.py
        secret.py
      build-ESP32_P4_CAM/
        firmware.bin                <- compiled during docker build (baked in)
  /opt/esp32-camera/                <- cloned esp32-camera IDF component
  /opt/idf/                         <- Espressif IDF v5.4 (from base image)

  Bind-mounted at docker run (overlays COPY'd versions with live host files):
  /opt/micropython/ports/esp32/boards/ESP32_P4_CAM/  <- micropython/boards/ESP32_P4_CAM/
  /opt/micropython/ports/esp32/modules_camera/        <- micropython/modules/
  /opt/micropython/ports/esp32/modules_frozen/        <- micropython/src/
  /firmware-out/                                      <- firmware-out/ on host

--- esp32p4-emulator ---

  Built from Dockerfile.qemu (three-stage). Runtime image:

  /usr/local/bin/
    qemu-system-riscv32    <- compiled from Espressif QEMU fork (Stage 1)
    mklittlefs             <- compiled from mklittlefs repo (Stage 2)
    run-qemu               <- COPY'd from scripts/run-qemu.sh (ENTRYPOINT)
    inject-scripts         <- COPY'd from scripts/inject-scripts.py

  /usr/local/share/qemu/   <- QEMU ROM blobs (COPY'd from Stage 1)

  /usr/bin/socat           <- from apt
  /usr/bin/python3         <- from apt
  /usr/local/bin/mpremote  <- from pip
  /usr/local/bin/esptool   <- from pip

  Bind-mounted at docker run:
  /firmware/               <- firmware-out/ on host  (contains firmware.bin)
  /scripts/                <- micropython/src/ on host  (boot.py, main.py)
  /secret.json             <- secret.json on host  (single file, read-only)

  Generated inside the container at startup by run-qemu.sh:
  /tmp/flash.bin           <- 8 MiB flash image (firmware.bin padded to full size)
  /tmp/littlefs.bin        <- packed littlefs filesystem image
  /tmp/scripts/
    boot.py                <- copied from /scripts/
    main.py                <- copied from /scripts/
    secret.json            <- generated (merges /secret.json + emulator overrides)


================================================================================
CAMERA MODES
================================================================================

--- How windows.camera.server/server.py fits into the project ---

  The ESP32-P4 firmware fetches JPEG frames over HTTP and publishes them over
  MQTT. In the QEMU emulator there is no camera hardware, so frames come from
  the camera-proxy Docker container. But camera-proxy runs inside Docker on
  WSL2 and cannot directly access the Windows built-in camera (Intel IPU /
  DirectShow). windows.camera.server/server.py bridges this gap -- it runs on Windows
  and serves frames over HTTP that Docker can reach via host.docker.internal.

  Windows built-in camera (DirectShow)
          | cv2.VideoCapture (DirectShow backend)
          v
  windows.camera.server/server.py       Windows process, port 8081
          | GET http://host.docker.internal:8081/frame.jpg
          v
  camera-proxy container         Docker/WSL2, port 8080
          | GET http://camera-proxy:8080/frame.jpg
          v
  esp32p4-emulator (MicroPython) QEMU, main.py fetches frame every 10 s
          | MQTT publish  devices/<thing>/image
          v
  localstack                     MQTT broker

  windows.camera.server/server.py is only needed when CAMERA_SOURCE=network (the
  default). Switch to v4l2 (USB webcam) or pattern (test pattern) and it
  is not required at all.

  CAMERA_SOURCE    Camera                         Setup required
  ---------------  -----------------------------  ----------------------------
  network          Windows built-in               Run windows.camera.server/server.py
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
  8081   windows.camera.server/server.py  (Windows side -- not in Docker)
  2323   esp32p4-emulator     Serial REPL  (mpremote / telnet)
  1234   esp32p4-emulator     QEMU GDB stub


================================================================================
MQTT TRANSPORT
================================================================================

  Runtime                          Port  Transport
  -------------------------------  ----  -----------------------------------------
  Emulator (emulator=true)         1883  Plain TCP -- SSL skipped entirely
  Real hardware -> LocalStack      8883  TLS, server cert not verified
                                         (mqtt_ssl_verify=false, self-signed)
  Real hardware -> AWS IoT Core    8883  Mutual TLS, server verified
                                         (mqtt_ssl_verify=true, AmazonRootCA1.pem)

  Run "make setup" after containers start to provision the IoT thing and save
  certs/device.pem.crt, certs/device.key, and certs/ca.pem (LocalStack CA).
  "make upload-scripts" pushes all cert files to the device alongside secret.json.


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

  Dockerfile.micropython          espressif/idf:v5.4 -> MicroPython firmware build
  Dockerfile.qemu                 Espressif QEMU + mklittlefs + runtime
  Dockerfile.camera-proxy         Python/OpenCV HTTP camera server
  docker-compose.yml              Reference only -- not used to run containers
  Makefile                        Shortcut targets (wraps docker commands)
  .env                            Active environment variables (committed, no secrets)
  .env.example                    Reference for all environment variable names
  .gitignore                      Excludes secret.json, certs/, firmware-out/, .venv/
  secret.json.example             Template for secret.json -- copy and fill in
  dov                             Project utility shell script

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
      boot.py                     WiFi connect via Secret.wifi_ssid/wifi_password()
      main.py                     Camera capture + MQTT publish every 10 s; SSL on hw
      secret.py                   Secret class -- reads secret.json from device flash

  scripts/
    run-qemu.sh                   Emulator entrypoint: flash image, socat, QEMU
    inject-scripts.py             Uploads .py files via mpremote after QEMU boots
    setup-localstack.sh           Provisions IoT thing / policy / cert on LocalStack
    provision-fleet.sh            Batch-provisions N devices in parallel (real AWS)
    generate-erp-pdf.py           Generates docs/erp-integration.pdf workflow diagrams
    generate-system-diagram.py    Generates docs/system.entity.diagram.pdf
    wait.for.localstack.sh        Block until LocalStack IoT healthy (120 s timeout)
    one.liner.wait-for-localstack.sh  Same as above as a single paste-friendly line
    requirements.txt              mpremote

  camera.proxy/
    server.py                     HTTP camera server -- Docker container entrypoint
    list_cameras.py               Probe available V4L2 devices before running server.py
    requirements.txt              opencv-python-headless, numpy
    backends/
      __init__.py                 Backend selection (CAMERA_SOURCE -> start())
      v4l2.py                     V4L2 capture loop (USB webcam via usbipd-win)
      network.py                  Network fetch loop (polls windows.camera.server)
      pattern.py                  Animated test pattern generator (NumPy)

  windows.camera.server/
    server.py                     Windows DirectShow camera HTTP server (run on Windows)
    list_cameras.py               Probe available camera indices before running server.py
    requirements.txt              opencv-python

  firmware/
    main/
      mqtt_main.c                 ESP-IDF C reference implementation (not MicroPython)
      CMakeLists.txt
      Kconfig.projbuild
    CMakeLists.txt
    sdkconfig.defaults.esp32p4   IDF sdkconfig defaults for ESP32-P4

  docs/
    erp-integration.pdf           Fleet workflow diagrams (generate-erp-pdf.py)
    system.entity.diagram.pdf     System entity interaction diagram (generate-system-diagram.py)

  firmware-out/                   firmware.bin lands here after build (git-ignored)
  certs/                          Device certs from LocalStack / AWS (git-ignored)
  secret.json                     Per-machine config -- never committed (git-ignored)


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
