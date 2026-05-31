#include "py/obj.h"
#include "py/runtime.h"
#include "py/mphal.h"
#include "esp_camera.h"
#include "esp_log.h"

static const char *TAG = "modcamera";
static bool s_initialized = false;

// ── camera.init(format, framesize, quality, fb_count) ─────────────────────────
static mp_obj_t camera_init(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args)
{
    enum { ARG_format, ARG_framesize, ARG_quality, ARG_fb_count };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_format,    MP_ARG_KW_ONLY | MP_ARG_INT, { .u_int = PIXFORMAT_JPEG } },
        { MP_QSTR_framesize, MP_ARG_KW_ONLY | MP_ARG_INT, { .u_int = FRAMESIZE_VGA  } },
        { MP_QSTR_quality,   MP_ARG_KW_ONLY | MP_ARG_INT, { .u_int = 12             } },
        { MP_QSTR_fb_count,  MP_ARG_KW_ONLY | MP_ARG_INT, { .u_int = 2              } },
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(n_args, pos_args, kw_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    if (s_initialized) {
        esp_camera_deinit();
        s_initialized = false;
    }

    // ESP32-P4 uses MIPI CSI-2; pin fields that apply to DVP are left -1.
    camera_config_t cfg = {
        .pin_pwdn       = -1,
        .pin_reset      = -1,
        .pin_xclk       = -1,  // CSI clock is internal on P4
        .pin_sccb_sda   = -1,
        .pin_sccb_scl   = -1,
        .pin_d7 = -1, .pin_d6 = -1, .pin_d5 = -1, .pin_d4 = -1,
        .pin_d3 = -1, .pin_d2 = -1, .pin_d1 = -1, .pin_d0 = -1,
        .pin_vsync      = -1,
        .pin_href       = -1,
        .pin_pclk       = -1,
        .xclk_freq_hz   = 20000000,
        .ledc_timer     = LEDC_TIMER_0,
        .ledc_channel   = LEDC_CHANNEL_0,
        .pixel_format   = (pixformat_t)args[ARG_format].u_int,
        .frame_size     = (framesize_t)args[ARG_framesize].u_int,
        .jpeg_quality   = args[ARG_quality].u_int,
        .fb_count       = args[ARG_fb_count].u_int,
        .grab_mode      = CAMERA_GRAB_LATEST,
        .fb_location    = CAMERA_FB_IN_PSRAM,
        .sccb_i2c_port  = 0,
    };

    esp_err_t err = esp_camera_init(&cfg);
    if (err != ESP_OK) {
        mp_raise_msg_varg(&mp_type_OSError, MP_ERROR_TEXT("camera init failed: %d"), err);
    }
    s_initialized = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_KW(camera_init_obj, 0, camera_init);

// ── camera.capture() → bytes | None ───────────────────────────────────────────
static mp_obj_t camera_capture(void)
{
    if (!s_initialized) {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("camera not initialized"));
    }
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
        ESP_LOGW(TAG, "frame buffer get failed");
        return mp_const_none;
    }
    mp_obj_t buf = mp_obj_new_bytes(fb->buf, fb->len);
    esp_camera_fb_return(fb);
    return buf;
}
static MP_DEFINE_CONST_FUN_OBJ_0(camera_capture_obj, camera_capture);

// ── camera.deinit() ────────────────────────────────────────────────────────────
static mp_obj_t camera_deinit(void)
{
    if (s_initialized) {
        esp_camera_deinit();
        s_initialized = false;
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(camera_deinit_obj, camera_deinit);

// ── Module table ───────────────────────────────────────────────────────────────
static const mp_rom_map_elem_t camera_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__),  MP_ROM_QSTR(MP_QSTR_camera)    },
    { MP_ROM_QSTR(MP_QSTR_init),      MP_ROM_PTR(&camera_init_obj)    },
    { MP_ROM_QSTR(MP_QSTR_capture),   MP_ROM_PTR(&camera_capture_obj) },
    { MP_ROM_QSTR(MP_QSTR_deinit),    MP_ROM_PTR(&camera_deinit_obj)  },

    // pixel format constants
    { MP_ROM_QSTR(MP_QSTR_JPEG),      MP_ROM_INT(PIXFORMAT_JPEG)    },
    { MP_ROM_QSTR(MP_QSTR_RGB565),    MP_ROM_INT(PIXFORMAT_RGB565)  },
    { MP_ROM_QSTR(MP_QSTR_YUV422),    MP_ROM_INT(PIXFORMAT_YUV422)  },
    { MP_ROM_QSTR(MP_QSTR_GRAYSCALE), MP_ROM_INT(PIXFORMAT_GRAYSCALE) },

    // frame size constants
    { MP_ROM_QSTR(MP_QSTR_QVGA),  MP_ROM_INT(FRAMESIZE_QVGA)  },   // 320x240
    { MP_ROM_QSTR(MP_QSTR_VGA),   MP_ROM_INT(FRAMESIZE_VGA)   },   // 640x480
    { MP_ROM_QSTR(MP_QSTR_SVGA),  MP_ROM_INT(FRAMESIZE_SVGA)  },   // 800x600
    { MP_ROM_QSTR(MP_QSTR_XGA),   MP_ROM_INT(FRAMESIZE_XGA)   },   // 1024x768
    { MP_ROM_QSTR(MP_QSTR_HD),    MP_ROM_INT(FRAMESIZE_HD)    },   // 1280x720
    { MP_ROM_QSTR(MP_QSTR_SXGA),  MP_ROM_INT(FRAMESIZE_SXGA)  },   // 1280x1024
    { MP_ROM_QSTR(MP_QSTR_UXGA),  MP_ROM_INT(FRAMESIZE_UXGA)  },   // 1600x1200
};
static MP_DEFINE_CONST_DICT(camera_module_globals, camera_module_globals_table);

const mp_obj_module_t mp_module_camera = {
    .base    = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&camera_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_camera, mp_module_camera);
