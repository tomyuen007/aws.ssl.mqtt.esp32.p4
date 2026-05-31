set(IDF_TARGET esp32p4)

# Inherit the generic P4 base config, then overlay camera additions
set(SDKCONFIG_DEFAULTS
    boards/sdkconfig.base
    boards/ESP32_P4_CAM/sdkconfig.board
)

# Pull in the camera C module
list(APPEND EXTRA_COMPONENT_DIRS $ENV{EXTRA_COMPONENT_DIRS})
