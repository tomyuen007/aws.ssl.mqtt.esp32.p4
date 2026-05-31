idf_component_register(
    SRCS "mqtt_main.c"
    INCLUDE_DIRS "."
    REQUIRES
        nvs_flash
        esp_wifi
        mqtt
        esp_event
        esp_netif
)
