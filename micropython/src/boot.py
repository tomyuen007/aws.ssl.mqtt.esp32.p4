import network
import time
from secret import Secret


def connect_wifi(retries=20):
    ssid     = Secret.wifi_ssid()
    password = Secret.wifi_password()
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return wlan.ifconfig()[0]
    wlan.connect(ssid, password)
    for _ in range(retries):
        if wlan.isconnected():
            break
        time.sleep_ms(500)
    if not wlan.isconnected():
        raise OSError("WiFi connect failed")
    ip = wlan.ifconfig()[0]
    print("WiFi:", ip)
    return ip


connect_wifi()
