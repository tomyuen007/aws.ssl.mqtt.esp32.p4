PORT      ?= /dev/ttyUSB0
BAUD      ?= 460800
THING     ?= esp32p4-device-01
BUILD_DIR  = /opt/micropython/ports/esp32

.PHONY: up down \
        build-firmware copy-firmware \
        build-emulator run-emulator \
        build-camera-proxy camera-preview \
        repl inject \
        setup flash erase upload-scripts monitor \
        clean

# ── Infrastructure ────────────────────────────────────────────────────────────
up:
	@mkdir -p firmware-out
	docker network create iot-net 2>/dev/null || true
	docker volume create localstack_data 2>/dev/null || true
	docker start localstack camera-proxy micropython-builder 2>/dev/null || true
	@echo "Waiting for LocalStack IoT..."
	@until docker exec localstack \
	    curl -sf http://localhost:4566/_localstack/health | grep -q '"iot"'; \
	    do sleep 2; done
	@echo "LocalStack ready."
	docker start esp32p4-emulator 2>/dev/null || true

down:
	docker stop esp32p4-emulator micropython-builder camera-proxy localstack 2>/dev/null || true

# ── Firmware build ────────────────────────────────────────────────────────────
build-firmware:
	docker exec micropython-builder \
	  bash -c "cd $(BUILD_DIR) && \
	    make BOARD=ESP32_P4_CAM \
	         USER_C_MODULES=modules_camera/micropython.cmake \
	         FROZEN_MANIFEST=modules_frozen/manifest.py \
	         -j\$$(nproc)"

copy-firmware:
	docker exec micropython-builder \
	  bash -c "cp $(BUILD_DIR)/build-ESP32_P4_CAM/firmware.bin /firmware-out/ && \
	           echo 'firmware.bin -> ./firmware-out/'"

# ── Emulator ──────────────────────────────────────────────────────────────────
WIN_CAMERA_PORT ?= 8081
windows-camera:
	@echo "Starting Windows camera server on port $(WIN_CAMERA_PORT)..."
	cmd.exe /c start "Windows Camera Server" \
	    python.exe "$(shell wslpath -w $(PWD)/scripts/windows-camera-server.py)" \
	    --port $(WIN_CAMERA_PORT)

build-emulator:
	docker build -t esp32p4-emulator:latest -f Dockerfile.qemu .

run-emulator:
	@test -f secret.json || \
	  { echo "ERROR: secret.json not found. Run: cp secret.json.example secret.json"; exit 1; }
	@test -f firmware-out/firmware.bin || \
	  { echo "ERROR: firmware-out/firmware.bin not found. Run: make copy-firmware"; exit 1; }
	docker run -d \
	  --name esp32p4-emulator \
	  --network iot-net \
	  -p 2323:2323 \
	  -p 1234:1234 \
	  -v "$$(pwd)/firmware-out:/firmware:ro" \
	  -v "$$(pwd)/micropython/src:/scripts:ro" \
	  -v "$$(pwd)/secret.json:/secret.json:ro" \
	  -e FIRMWARE_BIN=/firmware/firmware.bin \
	  -e SCRIPTS_DIR=/scripts \
	  -e HOST_SECRET=/secret.json \
	  -e FLASH_SIZE_MB=8 \
	  -e FS_OFFSET=0x200000 \
	  -e FS_SIZE_MB=2 \
	  -e MQTT_BROKER=10.0.2.2 \
	  -e MQTT_PORT=1883 \
	  -e "THING_NAME=$${THING_NAME:-esp32p4-device-01}" \
	  -e LOCALSTACK_HOST=localstack \
	  -e CAMERA_PROXY_HOST=camera-proxy \
	  -e CAMERA_PROXY_PORT=8080 \
	  -e SERIAL_PORT=2323 \
	  -e GDB_PORT=1234 \
	  esp32p4-emulator:latest
	@echo "Emulator starting...  attach with: make repl"

# ── Camera proxy ──────────────────────────────────────────────────────────────
build-camera-proxy:
	docker build -t esp32p4-camera-proxy:latest -f Dockerfile.camera-proxy .

camera-preview:
	@explorer.exe "http://localhost:8080/stream" 2>/dev/null || \
	 xdg-open "http://localhost:8080/stream" 2>/dev/null || \
	 echo "Open http://localhost:8080/stream in a browser"

# ── REPL and script injection ─────────────────────────────────────────────────
repl:
	mpremote connect socket://localhost:2323

inject:
	docker exec esp32p4-emulator \
	  inject-scripts --host localhost --port 2323 --dir /scripts

# ── LocalStack provisioning ───────────────────────────────────────────────────
setup:
	@test -f .env || { echo "ERROR: .env not found. Run: cp .env.example .env"; exit 1; }
	set -a && . ./.env && set +a && \
	AWS_ACCESS_KEY_ID=$${AWS_ACCESS_KEY_ID:-test} \
	AWS_SECRET_ACCESS_KEY=$${AWS_SECRET_ACCESS_KEY:-test} \
	THING_NAME=$${THING_NAME:-$(THING)} \
	bash scripts/setup-localstack.sh

# ── Physical device ───────────────────────────────────────────────────────────
flash: firmware-out/firmware.bin
	esptool.py --chip esp32p4 --port $(PORT) --baud $(BAUD) \
	    --before default_reset --after hard_reset \
	    write_flash --flash_mode dio --flash_size detect 0x0 \
	    firmware-out/firmware.bin

erase:
	esptool.py --chip esp32p4 --port $(PORT) erase_flash

# Uploads secret.json (WiFi credentials), boot.py, and main.py to the device.
# secret.py is already frozen in the firmware — no need to upload it separately.
upload-scripts:
	@test -f secret.json || \
	  { echo "ERROR: secret.json not found. Run: cp secret.json.example secret.json"; exit 1; }
	mpremote connect $(PORT) \
	    cp secret.json :secret.json + \
	    cp micropython/src/boot.py :boot.py + \
	    cp micropython/src/main.py :main.py + \
	    reset

monitor:
	mpremote connect $(PORT)

# ── Housekeeping ──────────────────────────────────────────────────────────────
clean:
	docker exec micropython-builder \
	  bash -c "cd $(BUILD_DIR) && make BOARD=ESP32_P4_CAM clean"
	rm -rf firmware-out/
