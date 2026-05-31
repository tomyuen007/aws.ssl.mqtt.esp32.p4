# Modules frozen into the firmware image.
# List files explicitly — do NOT use freeze(dir) here because this manifest.py
# lives in the same directory and would be compiled as a module (build error).
freeze("$(PORT_DIR)/modules_frozen", "secret.py")
freeze("$(PORT_DIR)/modules_frozen", "boot.py")
freeze("$(PORT_DIR)/modules_frozen", "main.py")

# umqtt from the MicroPython stdlib
require("umqtt.simple")
require("umqtt.robust")
