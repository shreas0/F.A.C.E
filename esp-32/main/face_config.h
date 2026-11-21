#pragma once

#define FACE_SERVER_HOST             "172.31.58.95"
#define FACE_SERVER_PORT             5001
#define FACE_UPLOAD_PATH             "/upload"

#define FACE_DEVICE_ID               "facecam-01"
#define FACE_NTP_SERVER              "pool.ntp.org"
#define FACE_TIME_ZONE               "IST-5:30"

#define FACE_DETECTION_FPS            5
#define FACE_OLED_PREVIEW_FPS         4
#define FACE_FACE_CLEAR_FRAMES        1
#define FACE_SUCCESS_COOLDOWN_SEC    1
#define FACE_FAILURE_RETRY_SEC       1
#define FACE_WIFI_CONNECT_TIMEOUT_MS 15000
#define FACE_HTTP_TIMEOUT_MS         15000
#define FACE_HTTP_RETRY_LIMIT        2
#define FACE_JPEG_QUALITY             12

#define FACE_NTP_WAIT_MS             20000
#define FACE_NTP_RETRY_SEC           60
#define FACE_UXGA_STABILIZE_MS      1200
#define FACE_CAMERA_RESTART_DELAY_MS 250
#define FACE_ENFORCE_OPERATING_HOURS 0

// AI-Thinker onboard flash LED (shared with the microSD interface); held off.
#define FACE_POWER_LED_GPIO           4

// The AI-Thinker camera does not use GPIO13/14 unless the microSD socket is used.
#define FACE_OLED_SDA_GPIO           13
#define FACE_OLED_SCL_GPIO           14
#define FACE_OLED_HEIGHT             64


