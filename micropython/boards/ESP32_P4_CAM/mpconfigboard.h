#define MICROPY_HW_BOARD_NAME  "ESP32-P4-CAM"
#define MICROPY_HW_MCU_NAME    "ESP32-P4"

// ── Camera module ──────────────────────────────────────────────────────────────
// Compiled-in camera module exposed as `import camera`
#define MODULE_CAMERA_ENABLED  (1)

// ── UART console ──────────────────────────────────────────────────────────────
#define MICROPY_HW_UART_REPL        (0)
#define MICROPY_HW_UART_REPL_BAUD   115200

// ── PSRAM ─────────────────────────────────────────────────────────────────────
// ESP32-P4 has internal PSRAM; frame buffers live here
#define MICROPY_HW_ENABLE_PSRAM     (1)
