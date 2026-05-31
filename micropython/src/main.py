import time
import ujson
from umqtt.robust import MQTTClient
from secret import Secret

THING_NAME       = Secret.thing_name()
MQTT_BROKER      = Secret.mqtt_broker()
MQTT_PORT        = Secret.mqtt_port()
EMULATOR         = Secret.is_emulator()
CAMERA_PROXY_URL = Secret.camera_proxy_url()

T_STATUS    = "devices/" + THING_NAME + "/status"
T_TELEMETRY = "devices/" + THING_NAME + "/telemetry"
T_IMAGE     = "devices/" + THING_NAME + "/image"
T_CMD       = "devices/" + THING_NAME + "/cmd"

CAPTURE_INTERVAL_MS = 10_000

# ── Camera ─────────────────────────────────────────────────────────────────────
_camera_ok = False

if not EMULATOR:
    import camera
    try:
        camera.init(format=camera.JPEG, framesize=camera.VGA, quality=12, fb_count=2)
        _camera_ok = True
        print("camera: hardware OK")
    except OSError as e:
        print("camera: init failed", e)

# Tiny 1x1 gray JPEG — last-resort fallback when proxy is also unreachable
_STUB_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
    b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1e"
    b"C  C\x00\x00\x08\x00\x08\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01"
    b"\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01"
    b"\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07"
    b"\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xf5\x00\xff\xd9"
)


def _fetch_proxy_frame(url):
    import socket
    url = url[7:]                          # strip "http://"
    host, rest = url.split("/", 1) if "/" in url else (url, "")
    path = "/" + rest
    host, port = (host.split(":") + ["80"])[:2]
    port = int(port)
    try:
        s = socket.socket()
        s.settimeout(3)
        s.connect((host, port))
        req = (
            "GET " + path + " HTTP/1.0\r\n"
            "Host: " + host + "\r\n"
            "Connection: close\r\n\r\n"
        ).encode()
        s.send(req)
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = s.recv(1)
            if not chunk:
                return None
            buf += chunk
        body = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            body += chunk
        s.close()
        return body if body else None
    except Exception as e:
        print("camera proxy fetch error:", e)
        return None


def capture_frame():
    if _camera_ok:
        return camera.capture()
    if CAMERA_PROXY_URL:
        frame = _fetch_proxy_frame(CAMERA_PROXY_URL)
        if frame:
            return frame
        print("camera: proxy unreachable, using stub")
    return _STUB_JPEG


# ── MQTT ───────────────────────────────────────────────────────────────────────
def on_cmd(topic, msg):
    print("cmd:", topic, msg)
    try:
        payload = ujson.loads(msg)
        if payload.get("framesize") and _camera_ok:
            camera.deinit()
            camera.init(
                format    = camera.JPEG,
                framesize = getattr(camera, payload["framesize"], camera.VGA),
                quality   = payload.get("quality", 12),
                fb_count  = 2,
            )
    except Exception as e:
        print("cmd error:", e)


client = MQTTClient(
    client_id = THING_NAME,
    server    = MQTT_BROKER,
    port      = MQTT_PORT,
    keepalive = 60,
)
client.set_callback(on_cmd)
client.connect()
client.subscribe(T_CMD)
client.publish(
    T_STATUS,
    ujson.dumps({
        "state":    "online",
        "chip":     "esp32p4",
        "emulator": EMULATOR,
        "camera":   "hardware" if _camera_ok else
                    ("proxy" if CAMERA_PROXY_URL else "stub"),
    }),
    retain=True,
    qos=1,
)
print("MQTT ->", MQTT_BROKER, ":", MQTT_PORT)

# ── Main loop ──────────────────────────────────────────────────────────────────
seq      = 0
last_cap = time.ticks_ms() - CAPTURE_INTERVAL_MS

while True:
    client.check_msg()

    now = time.ticks_ms()
    if time.ticks_diff(now, last_cap) >= CAPTURE_INTERVAL_MS:
        frame     = capture_frame()
        img_bytes = len(frame) if frame else 0

        if frame:
            client.publish(T_IMAGE, frame, qos=0)
            print("image:", img_bytes, "bytes")

        client.publish(
            T_TELEMETRY,
            ujson.dumps({
                "thing":    THING_NAME,
                "chip":     "esp32p4",
                "emulator": EMULATOR,
                "seq":      seq,
                "img_b":    img_bytes,
            }),
            qos=1,
        )
        seq     += 1
        last_cap = now

    time.sleep_ms(100)
