#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <cstring>
#include <list>
#include <vector>

#include "esp_camera.h"
#include "driver/gpio.h"
#include "esp_http_client.h"
#include "cJSON.h"
#include "esp_log.h"
#include "esp_psram.h"
#include "esp_random.h"
#include "esp_sleep.h"
#include "esp_timer.h"
#include "img_converters.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "human_face_detect_mnp01.hpp"
#include "human_face_detect_msr01.hpp"
#include "dl_image.hpp"

#include "face_config.h"
#include "face_display.h"
#include "wifi_manager.h"

namespace {

constexpr char TAG[] = "face_firmware";
constexpr int64_t DETECTION_PERIOD_US = 1000000LL / FACE_DETECTION_FPS;

bool s_camera_ready = false;

void flash_led_off()
{
    gpio_reset_pin(static_cast<gpio_num_t>(FACE_POWER_LED_GPIO));
    const esp_err_t err = gpio_set_direction(
        static_cast<gpio_num_t>(FACE_POWER_LED_GPIO), GPIO_MODE_OUTPUT);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "Could not configure flash LED off: %s", esp_err_to_name(err));
        return;
    }
    const esp_err_t level_err = gpio_set_level(
        static_cast<gpio_num_t>(FACE_POWER_LED_GPIO), 0);
    if (level_err != ESP_OK) {
        ESP_LOGW(TAG, "Could not hold flash LED low: %s", esp_err_to_name(level_err));
    }
}

bool is_operating_time(time_t now)
{
    struct tm local_time{};
    localtime_r(&now, &local_time);
    return local_time.tm_hour >= 9 && local_time.tm_hour < 17;
}

[[noreturn]] void sleep_until_next_open(time_t now)
{
    struct tm wake_time{};
    localtime_r(&now, &wake_time);
    const int current_hour = wake_time.tm_hour;
    wake_time.tm_hour = 9;
    wake_time.tm_min = 0;
    wake_time.tm_sec = 0;
    if (current_hour >= 17) {
        ++wake_time.tm_mday;
    }

    const time_t wake_epoch = std::mktime(&wake_time);
    const int64_t sleep_seconds = std::max<int64_t>(60, static_cast<int64_t>(wake_epoch - now));
    ESP_LOGI(TAG, "Outside operating hours; sleeping for %lld seconds",
             static_cast<long long>(sleep_seconds));
    face_display_show("WORK HOURS OVER", "SLEEPING", "BACK AT 9 AM IST", nullptr);
    wifi_manager_stop();
    esp_sleep_enable_timer_wakeup(static_cast<uint64_t>(sleep_seconds) * 1000000ULL);
    esp_deep_sleep_start();
    std::abort();
}

camera_config_t make_camera_config(pixformat_t pixel_format, framesize_t frame_size)
{
    camera_config_t config{};
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_pwdn = 32;
    config.pin_reset = -1;
    config.pin_xclk = 0;
    config.pin_sccb_sda = 26;
    config.pin_sccb_scl = 27;
    config.pin_d0 = 5;   // Y2
    config.pin_d1 = 18;  // Y3
    config.pin_d2 = 19;  // Y4
    config.pin_d3 = 21;  // Y5
    config.pin_d4 = 36;  // Y6
    config.pin_d5 = 39;  // Y7
    config.pin_d6 = 34;  // Y8
    config.pin_d7 = 35;  // Y9
    config.pin_xclk = 0;
    config.pin_pclk = 22;
    config.pin_vsync = 25;
    config.pin_href = 23;
    // The 3.84 MB raw UXGA stream can outrun the classic ESP32 camera DMA
    // copy path at 20 MHz. Use a slower sensor clock only for the still image.
    config.xclk_freq_hz = frame_size == FRAMESIZE_UXGA ? 5000000 : 20000000;
    config.pixel_format = pixel_format;
    config.frame_size = frame_size;
    config.jpeg_quality = FACE_JPEG_QUALITY;
    // Two QVGA buffers keep detection responsive. A UXGA RGB565 frame is
    // 3.84 MB, so a second buffer cannot fit in the ESP32's mapped PSRAM.
    config.fb_count = pixel_format == PIXFORMAT_RGB565 && frame_size == FRAMESIZE_QVGA ? 2 : 1;
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.grab_mode = config.fb_count > 1 ? CAMERA_GRAB_LATEST : CAMERA_GRAB_WHEN_EMPTY;
    return config;
}

void camera_stop();

bool camera_start(pixformat_t pixel_format, framesize_t frame_size,
                  bool show_detection_status = true)
{
    if (s_camera_ready) {
        camera_stop();
    }
    camera_config_t config = make_camera_config(pixel_format, frame_size);
    const esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        s_camera_ready = false;
        ESP_LOGE(TAG, "Camera init failed: %s", esp_err_to_name(err));
        face_display_show("CAMERA ERROR", "CHECK CAMERA CABLE", esp_err_to_name(err), nullptr);
        return false;
    }

    sensor_t *sensor = esp_camera_sensor_get();
    if (!sensor) {
        ESP_LOGE(TAG, "Camera sensor handle is unavailable");
        esp_camera_deinit();
        s_camera_ready = false;
        return false;
    }
    if (sensor->id.PID == OV2640_PID) {
        sensor->set_vflip(sensor, 1);
    }
    const char *pixel_format_name = pixel_format == PIXFORMAT_RGB565 ? "RGB565" :
                                    pixel_format == PIXFORMAT_JPEG ? "JPEG" : "other";
    const char *frame_size_name = frame_size == FRAMESIZE_QVGA ? "QVGA 320x240" :
                                  frame_size == FRAMESIZE_UXGA ? "UXGA 1600x1200" : "other";
    ESP_LOGI(TAG, "Camera ready: sensor PID=0x%04x, %s %s",
             sensor->id.PID, pixel_format_name, frame_size_name);
    if (frame_size == FRAMESIZE_UXGA) {
        face_display_show("CAPTURING IMAGE", "UXGA RGB565", "ENCODING JPEG...", nullptr);
    } else if (show_detection_status) {
        face_display_show(wifi_manager_test_mode_active() ? "TEST MODE" : "WORK MODE",
                          "FINDING FACE...", "QVGA CAMERA READY", nullptr);
    }
    s_camera_ready = true;
    return true;
}

void camera_stop()
{
    const esp_err_t err = esp_camera_deinit();
    s_camera_ready = false;
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGW(TAG, "Camera deinit reported: %s", esp_err_to_name(err));
    }
}

void draw_detection_boxes(camera_fb_t *frame,
                          const std::list<dl::detect::result_t> &candidates,
                          const std::list<dl::detect::result_t> &faces)
{
    if (!frame || frame->format != PIXFORMAT_RGB565 || !frame->buf) {
        return;
    }

    auto draw = [frame](const std::list<dl::detect::result_t> &detections,
                        uint16_t color) {
        for (const auto &detection : detections) {
            if (detection.box.size() < 4) {
                continue;
            }
            const int max_x = static_cast<int>(frame->width) - 1;
            const int max_y = static_cast<int>(frame->height) - 1;
            const int x1 = std::clamp(detection.box[0], 0, max_x);
            const int y1 = std::clamp(detection.box[1], 0, max_y);
            const int x2 = std::clamp(detection.box[2], 0, max_x);
            const int y2 = std::clamp(detection.box[3], 0, max_y);
            if (x2 > x1 && y2 > y1) {
                dl::image::draw_hollow_rectangle(
                    reinterpret_cast<uint16_t *>(frame->buf), frame->height,
                    frame->width, static_cast<uint32_t>(x1), static_cast<uint32_t>(y1),
                    static_cast<uint32_t>(x2), static_cast<uint32_t>(y2), color);
            }
        }
    };

    // Orange shows first-stage proposals; green boxes passed both detector stages.
    draw(candidates, 0xFD20);
    draw(faces, 0x07E0);
}

void write_base64_chunk(const uint8_t *data, size_t length)
{
    static constexpr char alphabet[] =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    char encoded[1025];
    size_t out = 0;
    for (size_t i = 0; i < length; i += 3) {
        const size_t remaining = length - i;
        const uint32_t value = (static_cast<uint32_t>(data[i]) << 16) |
            (remaining > 1 ? static_cast<uint32_t>(data[i + 1]) << 8 : 0) |
            (remaining > 2 ? static_cast<uint32_t>(data[i + 2]) : 0);
        encoded[out++] = alphabet[(value >> 18) & 0x3f];
        encoded[out++] = alphabet[(value >> 12) & 0x3f];
        encoded[out++] = remaining > 1 ? alphabet[(value >> 6) & 0x3f] : '=';
        encoded[out++] = remaining > 2 ? alphabet[value & 0x3f] : '=';
    }
    encoded[out] = '\0';
    std::printf("FACE_FRAME_DATA:%s\n", encoded);
    std::fflush(stdout);
}

void send_serial_preview(camera_fb_t *frame)
{
    if (!frame || frame->format != PIXFORMAT_RGB565 || !frame->buf) {
        ESP_LOGW(TAG, "Cannot preview: detection frame is not RGB565");
        return;
    }

    uint8_t *jpeg = nullptr;
    size_t jpeg_len = 0;
    if (!fmt2jpg(frame->buf, frame->len, frame->width, frame->height,
                 frame->format, FACE_JPEG_QUALITY, &jpeg, &jpeg_len) ||
        !jpeg || jpeg_len == 0) {
        ESP_LOGE(TAG, "Could not encode QVGA serial preview");
        std::free(jpeg);
        return;
    }

    std::printf("FACE_FRAME_BEGIN:%u:%u:%u\n",
                static_cast<unsigned>(jpeg_len), static_cast<unsigned>(frame->width),
                static_cast<unsigned>(frame->height));
    std::fflush(stdout);
    constexpr size_t SOURCE_CHUNK_BYTES = 768; // divisible by three for Base64 chunks
    for (size_t offset = 0; offset < jpeg_len; offset += SOURCE_CHUNK_BYTES) {
        const size_t chunk_len = std::min(SOURCE_CHUNK_BYTES, jpeg_len - offset);
        write_base64_chunk(jpeg + offset, chunk_len);
    }
    std::printf("FACE_FRAME_END\n");
    std::fflush(stdout);
    ESP_LOGI(TAG, "Sent %ux%u QVGA preview over USB serial (%u JPEG bytes)",
             static_cast<unsigned>(frame->width), static_cast<unsigned>(frame->height),
             static_cast<unsigned>(jpeg_len));
    std::free(jpeg);
}

struct JpegStreamContext {
    esp_http_client_handle_t client;
    size_t byte_count = 0;
    bool failed = false;
};

size_t count_jpeg_bytes(void *arg, size_t, const void *, size_t len)
{
    auto *context = static_cast<JpegStreamContext *>(arg);
    context->byte_count += len;
    return len;
}

size_t write_jpeg_chunk(void *arg, size_t, const void *data, size_t len)
{
    auto *context = static_cast<JpegStreamContext *>(arg);
    const char *bytes = static_cast<const char *>(data);
    size_t written = 0;
    while (written < len) {
        const int result = esp_http_client_write(context->client, bytes + written,
                                                static_cast<int>(len - written));
        if (result <= 0) {
            context->failed = true;
            return 0;
        }
        written += static_cast<size_t>(result);
    }
    context->byte_count += written;
    return written;
}

struct AttendanceResult {
    char status[24] = "unknown";
    char name[48] = "";
    char reason[32] = "missing_result";
};

void copy_json_string(char *target, size_t target_size, const cJSON *object,
                      const char *key, const char *fallback)
{
    const cJSON *item = cJSON_GetObjectItemCaseSensitive(object, key);
    const char *value = cJSON_IsString(item) && item->valuestring ? item->valuestring : fallback;
    std::snprintf(target, target_size, "%s", value);
}

bool upload_uxga_frame(camera_fb_t *frame, const char *capture_id,
                       AttendanceResult *attendance)
{
    if (!frame || frame->format != PIXFORMAT_RGB565 || !frame->buf ||
        frame->width != 1600 || frame->height != 1200 ||
        frame->len < static_cast<size_t>(frame->width) * frame->height * 2) {
        ESP_LOGE(TAG, "Refusing invalid UXGA RGB565 frame (format=%d, %ux%u, %u bytes)",
                 frame ? static_cast<int>(frame->format) : -1,
                 frame ? frame->width : 0, frame ? frame->height : 0,
                 frame ? static_cast<unsigned>(frame->len) : 0);
        return false;
    }

    // Count encoded bytes first, then stream the encoder output directly into
    // a fixed Content-Length HTTP request. This avoids a second multi-megabyte
    // UXGA allocation and keeps Flask's ordinary image/jpeg request handling.
    JpegStreamContext count_context{};
    if (!frame2jpg_cb(frame, FACE_JPEG_QUALITY, count_jpeg_bytes, &count_context) ||
        count_context.byte_count == 0 || count_context.byte_count > INT_MAX) {
        ESP_LOGE(TAG, "Could not encode UXGA RGB565 frame to JPEG");
        face_display_show("ENCODE FAILED", "UXGA TO JPEG", nullptr, nullptr);
        return false;
    }
    const size_t jpeg_length = count_context.byte_count;

    char url[160];
    std::snprintf(url, sizeof(url), "http://%s:%d%s", FACE_SERVER_HOST,
                  FACE_SERVER_PORT, FACE_UPLOAD_PATH);

    time_t now = std::time(nullptr);
    struct tm local_time{};
    localtime_r(&now, &local_time);
    char timestamp[40] = "unknown";
    std::strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%S%z", &local_time);

    ESP_LOGI(TAG, "Starting image transfer: POST %s (%u-byte UXGA JPEG, capture %s)",
             url, static_cast<unsigned>(jpeg_length), capture_id);

    for (int attempt = 1; attempt <= FACE_HTTP_RETRY_LIMIT; ++attempt) {
        char attempt_line[22];
        std::snprintf(attempt_line, sizeof(attempt_line), "TRY %d OF %d",
                      attempt, FACE_HTTP_RETRY_LIMIT);
        face_display_show("SENDING IMAGE", attempt_line, "FLASK /UPLOAD", nullptr);
        esp_http_client_config_t config{};
        config.url = url;
        config.method = HTTP_METHOD_POST;
        config.timeout_ms = FACE_HTTP_TIMEOUT_MS;
        config.buffer_size = 1024;
        config.buffer_size_tx = 1024;
        config.keep_alive_enable = false;

        esp_http_client_handle_t client = esp_http_client_init(&config);
        if (!client) {
            ESP_LOGE(TAG, "Could not create HTTP client");
            return false;
        }

        esp_http_client_set_header(client, "Content-Type", "image/jpeg");
        esp_http_client_set_header(client, "X-Device-ID", FACE_DEVICE_ID);
        esp_http_client_set_header(client, "X-Capture-ID", capture_id);
        esp_http_client_set_header(client, "X-Capture-Timestamp", timestamp);
        esp_http_client_set_header(client, "X-Image-Resolution", "1600x1200");
        esp_err_t err = esp_http_client_open(client, static_cast<int>(jpeg_length));
        JpegStreamContext stream_context{client};
        bool encoded = false;
        if (err == ESP_OK) {
            encoded = frame2jpg_cb(frame, FACE_JPEG_QUALITY, write_jpeg_chunk,
                                   &stream_context);
            if (!encoded || stream_context.failed || stream_context.byte_count != jpeg_length) {
                err = ESP_FAIL;
                ESP_LOGE(TAG, "JPEG stream failed (encoded=%d, wrote=%u of %u bytes)",
                         encoded, static_cast<unsigned>(stream_context.byte_count),
                         static_cast<unsigned>(jpeg_length));
            }
        }
        if (err == ESP_OK) {
            const int64_t response_length = esp_http_client_fetch_headers(client);
            if (response_length < 0) {
                err = ESP_FAIL;
            }
        }
        const int status = esp_http_client_get_status_code(client);
        char response_body[768]{};
        size_t response_used = 0;
        if (err == ESP_OK && status >= 200 && status < 300) {
            while (response_used + 1 < sizeof(response_body)) {
                const int received = esp_http_client_read(
                    client, response_body + response_used,
                    static_cast<int>(sizeof(response_body) - response_used - 1));
                if (received <= 0) break;
                response_used += static_cast<size_t>(received);
            }
            response_body[response_used] = '\0';
        }
        esp_http_client_close(client);
        esp_http_client_cleanup(client);
        if (err == ESP_OK && status >= 200 && status < 300) {
            ESP_LOGI(TAG, "JPEG uploaded (%u bytes, HTTP %d)",
                     static_cast<unsigned>(jpeg_length), status);
            face_display_show("IMAGE SENT", "IDENTIFYING...", "CHECKING ATTENDANCE", nullptr);
            cJSON *root = cJSON_Parse(response_body);
            const cJSON *result = root ? cJSON_GetObjectItemCaseSensitive(root, "attendance") : nullptr;
            if (attendance && cJSON_IsObject(result)) {
                copy_json_string(attendance->status, sizeof(attendance->status), result,
                                 "status", "unknown");
                copy_json_string(attendance->name, sizeof(attendance->name), result,
                                 "name", "");
                copy_json_string(attendance->reason, sizeof(attendance->reason), result,
                                 "reason", "");
            } else if (attendance) {
                std::snprintf(attendance->reason, sizeof(attendance->reason), "%s", "invalid_response");
            }
            if (root) cJSON_Delete(root);
            return true;
        }

        ESP_LOGW(TAG, "Upload attempt %d/%d failed (err=%s, HTTP %d)", attempt,
                 FACE_HTTP_RETRY_LIMIT, esp_err_to_name(err), status);
        face_display_show("UPLOAD RETRY", "CHECK SERVER", attempt_line, nullptr);
        if (attempt < FACE_HTTP_RETRY_LIMIT) {
            vTaskDelay(pdMS_TO_TICKS(1000));
        }
    }
    return false;
}

bool capture_high_resolution_and_upload(AttendanceResult *attendance)
{
    face_display_show("FACE CONFIRMED", "CAPTURING UXGA", "PLEASE WAIT...", nullptr);
    camera_stop();
    vTaskDelay(pdMS_TO_TICKS(FACE_CAMERA_RESTART_DELAY_MS));

    if (!camera_start(PIXFORMAT_RGB565, FRAMESIZE_UXGA)) {
        face_display_show("CAPTURE FAILED", "RESTORING CAMERA", nullptr, nullptr);
        camera_start(PIXFORMAT_RGB565, FRAMESIZE_QVGA, false);
        return false;
    }
    vTaskDelay(pdMS_TO_TICKS(FACE_UXGA_STABILIZE_MS));

    camera_fb_t *image = esp_camera_fb_get();
    if (!image || image->format != PIXFORMAT_RGB565 || image->len == 0 ||
        image->width != 1600 || image->height != 1200) {
        ESP_LOGE(TAG, "UXGA RGB565 capture invalid (frame=%p, format=%d, len=%u, %ux%u)",
                 static_cast<void *>(image), image ? static_cast<int>(image->format) : -1,
                 image ? static_cast<unsigned>(image->len) : 0,
                 image ? image->width : 0, image ? image->height : 0);
        face_display_show("CAPTURE FAILED", "BAD UXGA FRAME", nullptr, nullptr);
        if (image) {
            esp_camera_fb_return(image);
        }
        camera_stop();
        vTaskDelay(pdMS_TO_TICKS(FACE_CAMERA_RESTART_DELAY_MS));
        camera_start(PIXFORMAT_RGB565, FRAMESIZE_QVGA, false);
        return false;
    }

    char capture_id[64];
    std::snprintf(capture_id, sizeof(capture_id), "%s-%08lx", FACE_DEVICE_ID,
                  static_cast<unsigned long>(esp_random()));

    bool uploaded = false;
    face_display_show("IMAGE READY", "CONNECTING WIFI", nullptr, nullptr);
    if (wifi_manager_connect()) {
        uploaded = upload_uxga_frame(image, capture_id, attendance);
    } else {
        ESP_LOGE(TAG, "Image was captured but not sent: Wi-Fi connection failed");
    }
    wifi_manager_stop();
    esp_camera_fb_return(image);

    camera_stop();
    vTaskDelay(pdMS_TO_TICKS(FACE_CAMERA_RESTART_DELAY_MS));
    if (!camera_start(PIXFORMAT_RGB565, FRAMESIZE_QVGA, false)) {
        ESP_LOGE(TAG, "Could not restore QVGA detection mode");
    }
    return uploaded;
}

void wait_before_detection_retry()
{
    vTaskDelay(pdMS_TO_TICKS(5000));
}

} // namespace

extern "C" void app_main(void)
{
    setenv("TZ", FACE_TIME_ZONE, 1);
    tzset();
    flash_led_off();

    if (!esp_psram_is_initialized() || esp_psram_get_size() == 0) {
        ESP_LOGE(TAG, "PSRAM is not available; check the board and sdkconfig");
        face_display_init();
        face_display_show("PSRAM ERROR", "CAMERA CANNOT RUN", nullptr, nullptr);
        while (true) {
            vTaskDelay(pdMS_TO_TICKS(60000));
        }
    }
    ESP_LOGI(TAG, "PSRAM available: %u bytes", static_cast<unsigned>(esp_psram_get_size()));
    face_display_init();
    face_display_show("FACE CAM", "STARTING...", nullptr, nullptr);

    if (!wifi_manager_init()) {
        ESP_LOGE(TAG, "Wi-Fi manager initialization failed");
        face_display_show("STARTUP ERROR", "WIFI INIT FAILED", nullptr, nullptr);
        return;
    }

    bool time_synced = false;
    if (wifi_manager_test_mode_active()) {
        ESP_LOGW(TAG, "Starting in TEST MODE: skipping Wi-Fi/NTP; no captures will be uploaded");
        face_display_show("TEST MODE", "WIFI NOT NEEDED", "NO UPLOADS", "STARTING CAMERA");
    } else if (!wifi_manager_ensure_time_synced()) {
        ESP_LOGE(TAG, "Clock setup failed; camera remains idle");
        face_display_show("TIME SETUP ERROR", "CAMERA IS IDLE", nullptr, nullptr);
        return;
    } else {
        time_synced = true;
    }

    // Use ESP-WHO's recommended ESP32 thresholds and input resize for QVGA RGB565.
    HumanFaceDetectMSR01 stage_one(0.1F, 0.5F, 10, 0.2F);
    HumanFaceDetectMNP01 stage_two(0.5F, 0.3F, 5);
    int consecutive_absent = 0;
    bool wait_for_face_clear = false;
    int64_t success_cooldown_until_us = 0;
    int64_t failure_retry_after_us = 0;
    int64_t display_hold_until_us = 0;
    int64_t face_state_hold_until_us = 0;
    int64_t next_preview_us = 0;
    int64_t next_message_update_us = 0;

    while (true) {
        if (!wifi_manager_test_mode_active() && !time_synced) {
            if (!wifi_manager_ensure_time_synced()) {
                ESP_LOGE(TAG, "Could not synchronize time for WORK MODE");
                return;
            }
            time_synced = true;
        }

        if (wifi_manager_recovery_requested()) {
            camera_stop();
            if (!wifi_manager_ensure_time_synced()) {
                ESP_LOGE(TAG, "Wi-Fi recovery stopped; camera remains idle");
                return;
            }
            time_synced = true;
        }

        const time_t now = std::time(nullptr);
        if (FACE_ENFORCE_OPERATING_HOURS && !wifi_manager_test_mode_active() &&
            !is_operating_time(now)) {
            sleep_until_next_open(now);
        }

        if (!camera_start(PIXFORMAT_RGB565, FRAMESIZE_QVGA)) {
            face_display_show("CAMERA RETRY", "WAITING 5 SEC...", nullptr, nullptr);
            wait_before_detection_retry();
            continue;
        }
        ESP_LOGI(TAG, "Detection active: %s mode; QVGA RGB565 input",
                 wifi_manager_test_mode_active() ? "TEST" : "WORK");
        ESP_LOGI(TAG, "Detection pacing target: %u FPS; OLED preview limit: %u FPS",
                 FACE_DETECTION_FPS, FACE_OLED_PREVIEW_FPS);
        int64_t status_report_us = esp_timer_get_time();
        unsigned frames_since_report = 0;
        unsigned face_hits_since_report = 0;
        unsigned missing_frames_since_report = 0;
        uint64_t inference_time_total_us = 0;
        int64_t next_test_report_us = 0;

        while ((wifi_manager_test_mode_active() || !FACE_ENFORCE_OPERATING_HOURS ||
                is_operating_time(std::time(nullptr))) &&
               !wifi_manager_recovery_requested()) {
            const int64_t frame_started_us = esp_timer_get_time();
            camera_fb_t *frame = esp_camera_fb_get();
            if (!frame) {
                ESP_LOGW(TAG, "Camera returned no detection frame");
                ++missing_frames_since_report;
                vTaskDelay(pdMS_TO_TICKS(100));
                continue;
            }

            const unsigned frame_width = frame->width;
            const unsigned frame_height = frame->height;
            const unsigned frame_bytes = static_cast<unsigned>(frame->len);
            const pixformat_t frame_format = frame->format;
            std::list<dl::detect::result_t> empty_results;
            std::list<dl::detect::result_t> *candidates = &empty_results;
            std::list<dl::detect::result_t> *faces = &empty_results;
            const int64_t inference_started_us = esp_timer_get_time();
            if (frame->format == PIXFORMAT_RGB565 && frame->buf && frame->len > 0) {
                auto &stage_one_results = stage_one.infer(
                    reinterpret_cast<uint16_t *>(frame->buf),
                    {static_cast<int>(frame->height), static_cast<int>(frame->width), 3});
                auto &stage_two_results = stage_two.infer(
                    reinterpret_cast<uint16_t *>(frame->buf),
                    {static_cast<int>(frame->height), static_cast<int>(frame->width), 3},
                    stage_one_results);
                candidates = &stage_one_results;
                faces = &stage_two_results;
            }
            inference_time_total_us += static_cast<uint64_t>(
                esp_timer_get_time() - inference_started_us);

            const bool test_mode = wifi_manager_test_mode_active();
            const bool face_found = !faces->empty();
            const int64_t frame_now_us = esp_timer_get_time();
            bool trigger_capture = false;
            if (test_mode) {
                draw_detection_boxes(frame, *candidates, *faces);
                if (frame_now_us >= next_test_report_us) {
                    ESP_LOGI(TAG, "TEST MODE (uploads disabled): MSR proposals=%u, confirmed faces=%u",
                             static_cast<unsigned>(candidates->size()),
                             static_cast<unsigned>(faces->size()));
                    for (const auto &candidate : *candidates) {
                        if (candidate.box.size() >= 4) {
                            ESP_LOGI(TAG, "TEST proposal score=%.3f box=[%d,%d,%d,%d]",
                                     candidate.score, candidate.box[0], candidate.box[1],
                                     candidate.box[2], candidate.box[3]);
                        }
                    }
                    for (const auto &face : *faces) {
                        if (face.box.size() >= 4) {
                            ESP_LOGI(TAG, "TEST face score=%.3f box=[%d,%d,%d,%d]",
                                     face.score, face.box[0], face.box[1],
                                     face.box[2], face.box[3]);
                        }
                    }
                    next_test_report_us = frame_now_us + 1000000LL;
                }

                if (frame_now_us >= display_hold_until_us &&
                    frame_now_us >= next_preview_us) {
                    face_display_show("TEST MODE", face_found ? "FACE FOUND" : "DETECTING",
                                      "UPLOADS OFF", "TYPE MODE WORK TO UPLOAD");
                    next_preview_us = frame_now_us + 500000LL;
                }
                consecutive_absent = 0;
                wait_for_face_clear = false;
            } else if (face_found) {
                ++face_hits_since_report;
                consecutive_absent = 0;
                face_state_hold_until_us = frame_now_us + 1500000LL;

                if (wait_for_face_clear) {
                    if (frame_now_us >= next_message_update_us) {
                        char clear_line[24];
                        std::snprintf(clear_line, sizeof(clear_line), "CLEAR %d OF %d",
                                      consecutive_absent, FACE_FACE_CLEAR_FRAMES);
                        face_display_show("WAITING FOR CLEAR", "MOVE OUT OF VIEW",
                                          clear_line, nullptr);
                        next_message_update_us = frame_now_us + 500000LL;
                    }
                } else {
                    const int64_t blocked_until_us = std::max(success_cooldown_until_us,
                                                              failure_retry_after_us);
                    if (frame_now_us < blocked_until_us) {
                        const unsigned remaining_seconds = static_cast<unsigned>(
                            (blocked_until_us - frame_now_us + 999999LL) / 1000000LL);
                        char countdown[24];
                        std::snprintf(countdown, sizeof(countdown), "%u SECONDS",
                                      remaining_seconds);
                        if (frame_now_us >= next_message_update_us) {
                            const bool retrying = failure_retry_after_us >=
                                                  success_cooldown_until_us;
                            face_display_show(retrying ? "UPLOAD RETRY" : "COOLDOWN",
                                              retrying ? "RETRY IN" : "NEXT CAPTURE",
                                              countdown, "FACE DETECTED");
                            ESP_LOGI(TAG, "Face detected; %s is active for %u more seconds",
                                     retrying ? "upload retry cooldown" : "capture cooldown",
                                     remaining_seconds);
                            next_message_update_us = frame_now_us + 1000000LL;
                        }
                    } else {
                        ESP_LOGI(TAG, "Face detected in one frame; starting capture and upload");
                        face_display_show("FACE DETECTED", "CAPTURE STARTING",
                                          "STAY STILL", nullptr);
                        trigger_capture = true;
                    }
                }
            } else {
                if (wait_for_face_clear) {
                    ++consecutive_absent;
                    if (consecutive_absent >= FACE_FACE_CLEAR_FRAMES) {
                        wait_for_face_clear = false;
                        consecutive_absent = 0;
                        ESP_LOGI(TAG, "Face cleared; next detected face can trigger capture");
                        face_display_show("FACE CLEAR", "READY FOR NEXT FACE", nullptr, nullptr);
                        face_state_hold_until_us = frame_now_us + 1000000LL;
                    } else if (frame_now_us >= next_message_update_us) {
                        char clear_line[24];
                        std::snprintf(clear_line, sizeof(clear_line), "CLEAR %d OF %d",
                                      consecutive_absent, FACE_FACE_CLEAR_FRAMES);
                        face_display_show("WAITING FOR CLEAR", "MOVE OUT OF VIEW",
                                          clear_line, nullptr);
                        next_message_update_us = frame_now_us + 500000LL;
                    }
                }

                if (frame_now_us >= display_hold_until_us &&
                    frame_now_us >= face_state_hold_until_us &&
                    frame_now_us >= next_preview_us) {
                    if (frame->format == PIXFORMAT_RGB565 && frame->buf) {
                        face_display_show_camera_frame(
                            reinterpret_cast<const uint16_t *>(frame->buf),
                            frame->width, frame->height);
                    } else {
                        face_display_show("CAMERA FORMAT", "NOT RGB565", nullptr, nullptr);
                    }
                    next_preview_us = frame_now_us + 1000000LL / FACE_OLED_PREVIEW_FPS;
                }
            }
            if (wifi_manager_take_frame_request()) {
                send_serial_preview(frame);
            }
            esp_camera_fb_return(frame);
            ++frames_since_report;

            const int64_t report_now_us = esp_timer_get_time();
            if (report_now_us - status_report_us >= 10000000LL) {
                const uint64_t elapsed_us = static_cast<uint64_t>(report_now_us - status_report_us);
                const uint64_t fps_tenths = elapsed_us ?
                    (static_cast<uint64_t>(frames_since_report) * 10000000ULL) / elapsed_us : 0;
                const unsigned average_inference_ms = frames_since_report ?
                    static_cast<unsigned>(inference_time_total_us /
                                           frames_since_report / 1000ULL) : 0;
                ESP_LOGI(TAG,
                         "Detection rate %llu.%llu FPS (target %u); avg inference %u ms; "
                         "%u face hits, %u missing frames; frame %ux%u format=%d bytes=%u",
                         static_cast<unsigned long long>(fps_tenths / 10),
                         static_cast<unsigned long long>(fps_tenths % 10),
                         FACE_DETECTION_FPS, average_inference_ms, face_hits_since_report,
                         missing_frames_since_report,
                         frame_width, frame_height,
                         static_cast<int>(frame_format), frame_bytes);
                status_report_us = report_now_us;
                frames_since_report = 0;
                face_hits_since_report = 0;
                missing_frames_since_report = 0;
                inference_time_total_us = 0;
            }

            if (trigger_capture) {
                AttendanceResult attendance{};
                const bool uploaded = capture_high_resolution_and_upload(&attendance);
                consecutive_absent = 0;
                if (uploaded) {
                    wait_for_face_clear = true;
                    success_cooldown_until_us = esp_timer_get_time() +
                        static_cast<int64_t>(FACE_SUCCESS_COOLDOWN_SEC) * 1000000LL;
                    ESP_LOGI(TAG, "Upload completed. Cooldown=%d sec; face-clear requirement=%d frames",
                             FACE_SUCCESS_COOLDOWN_SEC, FACE_FACE_CLEAR_FRAMES);
                    if (std::strcmp(attendance.status, "marked") == 0) {
                        face_display_show("ATTENDANCE MARKED", attendance.name, "PRESENT", nullptr);
                    } else if (std::strcmp(attendance.status, "already_marked") == 0) {
                        face_display_show("ALREADY MARKED", attendance.name, "PRESENT TODAY", nullptr);
                    } else if (std::strcmp(attendance.reason, "session_inactive") == 0) {
                        face_display_show("NOT MARKED", attendance.name, "SESSION INACTIVE", nullptr);
                    } else if (std::strcmp(attendance.reason, "unknown") == 0 ||
                               std::strcmp(attendance.reason, "no_face") == 0) {
                        face_display_show("NOT MARKED", "UNKNOWN FACE", "IMAGE UPLOADED", nullptr);
                    } else if (attendance.name[0] != '\0') {
                        face_display_show("NOT MARKED", attendance.name, "DATABASE ERROR", nullptr);
                    } else {
                        face_display_show("NOT MARKED", "IMAGE UPLOADED", "CHECK SERVER", nullptr);
                    }
                } else {
                    failure_retry_after_us = esp_timer_get_time() +
                        static_cast<int64_t>(FACE_FAILURE_RETRY_SEC) * 1000000LL;
                    ESP_LOGW(TAG, "Upload did not complete; retry in %d sec",
                             FACE_FAILURE_RETRY_SEC);
                    face_display_show("UPLOAD FAILED", "RETRY IN 5 SEC", "CHECK WIFI / SERVER", nullptr);
                }
                display_hold_until_us = esp_timer_get_time() + 5000000LL;
                face_state_hold_until_us = display_hold_until_us;
                next_preview_us = display_hold_until_us;
                status_report_us = esp_timer_get_time();
                frames_since_report = 0;
                face_hits_since_report = 0;
                missing_frames_since_report = 0;
                inference_time_total_us = 0;
                if (!s_camera_ready || wifi_manager_recovery_requested()) {
                    break;
                }
            }

            const int64_t remaining_us = DETECTION_PERIOD_US -
                                         (esp_timer_get_time() - frame_started_us);
            if (remaining_us > 0) {
                vTaskDelay(pdMS_TO_TICKS(static_cast<uint32_t>((remaining_us + 999) / 1000)));
            }
        }

        camera_stop();
    }
}
