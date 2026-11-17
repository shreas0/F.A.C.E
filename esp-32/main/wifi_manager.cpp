#include "wifi_manager.h"

#include <atomic>
#include <cstdio>
#include <cstring>
#include <ctime>

#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_netif_sntp.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "nvs.h"
#include "nvs_flash.h"

#include "face_config.h"
#include "face_display.h"

namespace {

constexpr char TAG[] = "face_wifi";
constexpr EventBits_t WIFI_CONNECTED_BIT = BIT0;
constexpr EventBits_t WIFI_FAILED_BIT = BIT1;
constexpr int WIFI_RETRY_LIMIT = 5;
constexpr size_t WIFI_SSID_MAX_BYTES = sizeof(((wifi_config_t *)nullptr)->sta.ssid);
constexpr size_t WIFI_PASSWORD_MAX_BYTES = sizeof(((wifi_config_t *)nullptr)->sta.password);
constexpr size_t SERIAL_LINE_CAPACITY = 128;

struct Credentials {
    uint8_t ssid[WIFI_SSID_MAX_BYTES]{};
    size_t ssid_len = 0;
    uint8_t password[WIFI_PASSWORD_MAX_BYTES]{};
    size_t password_len = 0;
};

struct SerialLine {
    char text[SERIAL_LINE_CAPACITY]{};
    bool overflow = false;
};

enum class ReadResult { Ok, TooLong, Reset };

EventGroupHandle_t s_wifi_events = nullptr;
QueueHandle_t s_serial_lines = nullptr;
esp_netif_t *s_wifi_netif = nullptr;
esp_event_handler_instance_t s_wifi_event_handler = nullptr;
esp_event_handler_instance_t s_ip_event_handler = nullptr;
Credentials s_credentials{};
std::atomic<int> s_wifi_retry_count{0};
std::atomic<bool> s_wifi_initialized{false};
std::atomic<bool> s_wifi_stopping{false};
std::atomic<bool> s_wifi_had_ip{false};
std::atomic<bool> s_connection_failed{false};
std::atomic<bool> s_reset_requested{false};
std::atomic<bool> s_prompt_active{false};
std::atomic<bool> s_frame_requested{false};
std::atomic<bool> s_test_mode_active{false};

void wifi_event_callback(void *handler_arg, esp_event_base_t event_base,
                         int32_t event_id, void *event_data);

const char *disconnect_reason_hint(uint8_t reason)
{
    switch (reason) {
    case WIFI_REASON_AUTH_FAIL:
    case WIFI_REASON_4WAY_HANDSHAKE_TIMEOUT:
        return "authentication failed; check the password and router security mode";
    case WIFI_REASON_NO_AP_FOUND:
        return "access point not found; check the SSID and 2.4 GHz coverage";
    case WIFI_REASON_ASSOC_FAIL:
        return "association rejected by the access point";
    case WIFI_REASON_BEACON_TIMEOUT:
        return "beacon timeout; check signal strength and router stability";
    default:
        return "see the numeric reason code and check router/security settings";
    }
}

void emit_serial_line(const SerialLine &line)
{
    if (std::strcmp(line.text, "wifi reset") == 0 && !line.overflow) {
        s_reset_requested.store(true);
        face_display_show("WIFI RESET", "ENTER CREDENTIALS", nullptr, nullptr);
    }
    if (std::strcmp(line.text, "frame") == 0 && !line.overflow &&
        !s_prompt_active.load()) {
        s_frame_requested.store(true);
        return;
    }
    if (std::strcmp(line.text, "mode test") == 0 && !line.overflow &&
        !s_prompt_active.load()) {
        s_test_mode_active.store(true);
        ESP_LOGI(TAG, "TEST MODE enabled: schedule bypassed; no photo upload");
        face_display_show("TEST MODE", "DETECTION ONLY", "NO WIFI / UPLOAD", "FINDING FACE");
        return;
    }
    if (std::strcmp(line.text, "mode work") == 0 && !line.overflow &&
        !s_prompt_active.load()) {
        s_test_mode_active.store(false);
        ESP_LOGI(TAG, "WORK MODE enabled: schedule, face confirmation, and uploads active");
        face_display_show("WORK MODE", "RESTORING WIFI", "SYNCING TIME...", nullptr);
        return;
    }

    if (s_prompt_active.load()) {
        if (xQueueSend(s_serial_lines, &line, 0) != pdTRUE) {
            ESP_LOGW(TAG, "Serial input queue full; line discarded");
        }
    }
}

void serial_input_task(void *)
{
    SerialLine line{};
    size_t used = 0;
    bool skip_lf_after_cr = false;

    while (true) {
        const int ch = std::getchar();
        if (ch == EOF) {
            vTaskDelay(pdMS_TO_TICKS(10));
            continue;
        }

        if (skip_lf_after_cr) {
            skip_lf_after_cr = false;
            if (ch == '\n') {
                continue;
            }
        }

        if (ch == '\r' || ch == '\n') {
            if (ch == '\r') {
                skip_lf_after_cr = true;
            }
            line.text[used] = '\0';
            emit_serial_line(line);
            line = SerialLine{};
            used = 0;
            continue;
        }

        if (ch == '\b' || ch == 0x7f) {
            if (used > 0) {
                --used;
                line.text[used] = '\0';
            }
            continue;
        }

        if (ch < 0x20 || ch > 0x7e) {
            // UTF-8 SSIDs are accepted byte-for-byte; reject only control bytes.
            if (ch < 0x80) {
                continue;
            }
        }

        if (used + 1 < sizeof(line.text)) {
            line.text[used++] = static_cast<char>(ch);
        } else {
            line.overflow = true;
        }
    }
}

ReadResult read_prompt_line(const char *prompt, char *buffer, size_t capacity)
{
    while (true) {
        SerialLine stale{};
        while (xQueueReceive(s_serial_lines, &stale, 0) == pdTRUE) {
        }

        s_prompt_active.store(true);
        std::printf("%s", prompt);
        std::fflush(stdout);

        SerialLine line{};
        if (xQueueReceive(s_serial_lines, &line, portMAX_DELAY) != pdTRUE) {
            s_prompt_active.store(false);
            continue;
        }
        s_prompt_active.store(false);

        if (!line.overflow && std::strcmp(line.text, "wifi reset") == 0) {
            s_reset_requested.store(true);
            std::printf("\r\n");
            return ReadResult::Reset;
        }
        if (line.overflow || std::strlen(line.text) >= capacity) {
            std::printf("Input is too long; nothing was saved. Please try again.\r\n");
            continue;
        }

        std::strcpy(buffer, line.text);
        std::printf("\r\n");
        return ReadResult::Ok;
    }
}

void show_wifi_setup_banner()
{
    std::printf("\r\n====================================\r\n"
                "       F.A.C.E. Wi-Fi Setup\r\n"
                "====================================\r\n\r\n");
    std::fflush(stdout);
}

esp_err_t erase_credential_keys()
{
    nvs_handle_t handle;
    esp_err_t err = nvs_open("face_wifi", NVS_READWRITE, &handle);
    if (err != ESP_OK) {
        return err;
    }

    const char *keys[] = {"configured", "ssid", "password"};
    for (const char *key : keys) {
        const esp_err_t erase_err = nvs_erase_key(handle, key);
        if (erase_err != ESP_OK && erase_err != ESP_ERR_NVS_NOT_FOUND) {
            nvs_close(handle);
            return erase_err;
        }
    }
    err = nvs_commit(handle);
    nvs_close(handle);
    return err;
}

bool save_credentials(const Credentials &credentials)
{
    nvs_handle_t handle;
    esp_err_t err = nvs_open("face_wifi", NVS_READWRITE, &handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Cannot open credential storage: %s", esp_err_to_name(err));
        return false;
    }

    err = nvs_set_blob(handle, "ssid", credentials.ssid, credentials.ssid_len);
    if (err == ESP_OK && credentials.password_len > 0) {
        err = nvs_set_blob(handle, "password", credentials.password,
                           credentials.password_len);
    } else if (err == ESP_OK) {
        const esp_err_t erase_err = nvs_erase_key(handle, "password");
        if (erase_err != ESP_OK && erase_err != ESP_ERR_NVS_NOT_FOUND) {
            err = erase_err;
        }
    }
    if (err == ESP_OK) {
        err = nvs_set_u8(handle, "configured", 1);
    }
    if (err == ESP_OK) {
        err = nvs_commit(handle);
    }
    nvs_close(handle);

    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Could not save Wi-Fi credentials: %s", esp_err_to_name(err));
        return false;
    }
    ESP_LOGI(TAG, "Wi-Fi credentials saved in NVS");
    return true;
}

bool load_credentials(bool *found)
{
    *found = false;
    nvs_handle_t handle;
    esp_err_t err = nvs_open("face_wifi", NVS_READONLY, &handle);
    if (err == ESP_ERR_NVS_NOT_FOUND) {
        return true;
    }
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Cannot open Wi-Fi NVS namespace: %s", esp_err_to_name(err));
        return false;
    }

    uint8_t configured = 0;
    err = nvs_get_u8(handle, "configured", &configured);
    if (err == ESP_ERR_NVS_NOT_FOUND || (err == ESP_OK && configured == 0)) {
        nvs_close(handle);
        return true;
    }
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Cannot read Wi-Fi credential marker: %s", esp_err_to_name(err));
        nvs_close(handle);
        return false;
    }

    Credentials loaded{};
    size_t ssid_len = 0;
    err = nvs_get_blob(handle, "ssid", nullptr, &ssid_len);
    if (err != ESP_OK || ssid_len == 0 || ssid_len > sizeof(loaded.ssid)) {
        ESP_LOGW(TAG, "Saved SSID is missing or invalid; requesting credentials again");
        nvs_close(handle);
        return true;
    }
    loaded.ssid_len = ssid_len;
    err = nvs_get_blob(handle, "ssid", loaded.ssid, &loaded.ssid_len);
    if (err != ESP_OK) {
        nvs_close(handle);
        ESP_LOGE(TAG, "Cannot read saved SSID: %s", esp_err_to_name(err));
        return false;
    }

    size_t password_len = 0;
    err = nvs_get_blob(handle, "password", nullptr, &password_len);
    if (err == ESP_OK) {
        if (password_len > sizeof(loaded.password)) {
            ESP_LOGW(TAG, "Saved Wi-Fi password is invalid; requesting credentials again");
            nvs_close(handle);
            return true;
        }
        loaded.password_len = password_len;
        if (password_len > 0) {
            err = nvs_get_blob(handle, "password", loaded.password,
                               &loaded.password_len);
            if (err != ESP_OK) {
                nvs_close(handle);
                ESP_LOGE(TAG, "Cannot read saved Wi-Fi password: %s", esp_err_to_name(err));
                return false;
            }
        }
    } else if (err != ESP_ERR_NVS_NOT_FOUND) {
        nvs_close(handle);
        ESP_LOGE(TAG, "Cannot inspect saved Wi-Fi password: %s", esp_err_to_name(err));
        return false;
    }

    nvs_close(handle);
    s_credentials = loaded;
    *found = true;
    ESP_LOGI(TAG, "Loaded saved Wi-Fi credentials (password hidden)");
    return true;
}

bool prompt_for_credentials()
{
    while (true) {
        face_display_show("WIFI SETUP", "ENTER SSID + KEY", "USE SERIAL MONITOR", nullptr);
        show_wifi_setup_banner();
        char ssid[WIFI_SSID_MAX_BYTES + 2]{};
        char password[WIFI_PASSWORD_MAX_BYTES + 2]{};

        const ReadResult ssid_result = read_prompt_line("Enter your Wi-Fi SSID:\r\n", ssid,
                                                         sizeof(ssid));
        if (ssid_result == ReadResult::Reset) {
            s_reset_requested.store(false);
            const esp_err_t err = erase_credential_keys();
            if (err != ESP_OK) {
                ESP_LOGE(TAG, "Could not erase saved credentials: %s", esp_err_to_name(err));
                return false;
            }
            continue;
        }
        const size_t ssid_len = std::strlen(ssid);
        if (ssid_len == 0 || ssid_len > WIFI_SSID_MAX_BYTES) {
            std::printf("SSID must contain 1 to %u bytes.\r\n",
                        static_cast<unsigned>(WIFI_SSID_MAX_BYTES));
            continue;
        }

        const ReadResult password_result = read_prompt_line(
            "Enter your Wi-Fi password:\r\n", password, sizeof(password));
        if (password_result == ReadResult::Reset) {
            s_reset_requested.store(false);
            const esp_err_t err = erase_credential_keys();
            if (err != ESP_OK) {
                ESP_LOGE(TAG, "Could not erase saved credentials: %s", esp_err_to_name(err));
                return false;
            }
            continue;
        }
        const size_t password_len = std::strlen(password);
        if (password_len > WIFI_PASSWORD_MAX_BYTES) {
            std::printf("Password is too long (maximum %u bytes).\r\n",
                        static_cast<unsigned>(WIFI_PASSWORD_MAX_BYTES));
            continue;
        }

        Credentials entered{};
        entered.ssid_len = ssid_len;
        entered.password_len = password_len;
        std::memcpy(entered.ssid, ssid, ssid_len);
        if (password_len > 0) {
            std::memcpy(entered.password, password, password_len);
        }
        std::memset(password, 0, sizeof(password));
        std::memset(ssid, 0, sizeof(ssid));

        if (!save_credentials(entered)) {
            return false;
        }
        s_credentials = entered;
        return true;
    }
}

bool initialize_network_stack()
{
    esp_err_t err = esp_netif_init();
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGE(TAG, "esp_netif_init failed: %s", esp_err_to_name(err));
        return false;
    }

    err = esp_event_loop_create_default();
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGE(TAG, "Default event loop failed: %s", esp_err_to_name(err));
        return false;
    }

    s_wifi_events = xEventGroupCreate();
    if (!s_wifi_events) {
        ESP_LOGE(TAG, "Could not create Wi-Fi event group");
        return false;
    }

    s_wifi_netif = esp_netif_create_default_wifi_sta();
    if (!s_wifi_netif) {
        ESP_LOGE(TAG, "Could not create Wi-Fi station interface");
        return false;
    }

    wifi_init_config_t wifi_init_config = WIFI_INIT_CONFIG_DEFAULT();
    err = esp_wifi_init(&wifi_init_config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_wifi_init failed: %s", esp_err_to_name(err));
        return false;
    }

    err = esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID,
                                               wifi_event_callback, nullptr,
                                               &s_wifi_event_handler);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Could not register Wi-Fi events: %s", esp_err_to_name(err));
        return false;
    }
    err = esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP,
                                               wifi_event_callback, nullptr,
                                               &s_ip_event_handler);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Could not register IP events: %s", esp_err_to_name(err));
        return false;
    }

    s_wifi_initialized.store(true);
    return true;
}

void wifi_event_callback(void *, esp_event_base_t event_base, int32_t event_id,
                         void *event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        s_wifi_stopping.store(false);
        s_wifi_retry_count.store(0);
        const esp_err_t err = esp_wifi_connect();
        face_display_show("CONNECTING WIFI", "LOOKING FOR AP...", nullptr, nullptr);
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "Initial esp_wifi_connect failed: %s", esp_err_to_name(err));
            s_connection_failed.store(true);
            xEventGroupSetBits(s_wifi_events, WIFI_FAILED_BIT);
        }
        return;
    }

    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        face_display_set_wifi_connected(false);
        const auto *event = static_cast<const wifi_event_sta_disconnected_t *>(event_data);
        const uint8_t reason = event ? event->reason : 0;
        if (s_wifi_stopping.load()) {
            return;
        }

        const bool had_ip = s_wifi_had_ip.load();
        const int attempt = s_wifi_retry_count.fetch_add(1) + 1;
        ESP_LOGW(TAG, "Wi-Fi disconnected (reason=%u: %s), retry %d/%d%s",
                 static_cast<unsigned>(reason), disconnect_reason_hint(reason), attempt,
                 WIFI_RETRY_LIMIT, had_ip ? " after IP acquisition" : "");
        face_display_show("WIFI DISCONNECTED", "RETRYING...", nullptr, nullptr);
        if (attempt <= WIFI_RETRY_LIMIT) {
            char retry_line[32];
            std::snprintf(retry_line, sizeof(retry_line), "RETRY %d OF %d",
                          attempt, WIFI_RETRY_LIMIT);
            face_display_show("WIFI DISCONNECTED", retry_line, nullptr, nullptr);
            const esp_err_t err = esp_wifi_connect();
            if (err == ESP_OK) {
                return;
            }
            ESP_LOGW(TAG, "esp_wifi_connect retry failed: %s", esp_err_to_name(err));
        }

        s_connection_failed.store(true);
        xEventGroupSetBits(s_wifi_events, WIFI_FAILED_BIT);
        face_display_show("WIFI FAILED", "CHECK ROUTER", nullptr, nullptr);
        return;
    }

    if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP && s_wifi_events) {
        const auto *event = static_cast<const ip_event_got_ip_t *>(event_data);
        s_wifi_retry_count.store(0);
        s_wifi_had_ip.store(true);
        face_display_set_wifi_connected(true);
        s_connection_failed.store(false);
        xEventGroupSetBits(s_wifi_events, WIFI_CONNECTED_BIT);
        if (event) {
            ESP_LOGI(TAG, "DHCP assigned IP " IPSTR ", gateway " IPSTR,
                     IP2STR(&event->ip_info.ip), IP2STR(&event->ip_info.gw));
            char ip_line[22];
            std::snprintf(ip_line, sizeof(ip_line), "IP " IPSTR,
                          IP2STR(&event->ip_info.ip));
            face_display_show("WIFI CONNECTED", ip_line, "GETTING NETWORK TIME", nullptr);
        } else {
            ESP_LOGI(TAG, "Wi-Fi acquired an IP address");
            face_display_show("WIFI CONNECTED", "GETTING NETWORK TIME", nullptr, nullptr);
        }
    }
}

bool read_recovery_choice()
{
    while (true) {
        if (s_reset_requested.exchange(false)) {
            const esp_err_t err = erase_credential_keys();
            if (err != ESP_OK) {
                ESP_LOGE(TAG, "Could not erase saved credentials: %s", esp_err_to_name(err));
                return false;
            }
            std::memset(&s_credentials, 0, sizeof(s_credentials));
            return prompt_for_credentials();
        }

        face_display_show("WIFI NEEDS HELP", "TYPE RETRY OR NEW", "OR WIFI RESET", nullptr);
        char choice[SERIAL_LINE_CAPACITY]{};
        const ReadResult result = read_prompt_line(
            "Type 'retry' to retry, 'new' for different credentials, or 'wifi reset' to erase and set up again:\r\n",
            choice, sizeof(choice));
        const bool reset_was_pending = s_reset_requested.exchange(false);
        if (result == ReadResult::Reset || reset_was_pending) {
            const esp_err_t err = erase_credential_keys();
            if (err != ESP_OK) {
                ESP_LOGE(TAG, "Could not erase saved credentials: %s", esp_err_to_name(err));
                return false;
            }
            std::memset(&s_credentials, 0, sizeof(s_credentials));
            return prompt_for_credentials();
        }
        if (result == ReadResult::TooLong) {
            continue;
        }
        if (std::strcmp(choice, "retry") == 0) {
            return true;
        }
        if (std::strcmp(choice, "new") == 0) {
            return prompt_for_credentials();
        }
        std::printf("Unknown command.\r\n");
    }
}

} // namespace

bool wifi_manager_init()
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGW(TAG, "NVS needs recovery (%s); erasing and reinitializing",
                 esp_err_to_name(err));
        err = nvs_flash_erase();
        if (err == ESP_OK) {
            err = nvs_flash_init();
        }
    }
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "NVS initialization failed: %s", esp_err_to_name(err));
        return false;
    }

    s_serial_lines = xQueueCreate(4, sizeof(SerialLine));
    if (!s_serial_lines) {
        ESP_LOGE(TAG, "Could not create serial input queue");
        return false;
    }
    if (xTaskCreate(serial_input_task, "face_serial", 4096, nullptr, 5, nullptr) != pdPASS) {
        ESP_LOGE(TAG, "Could not start serial input task");
        return false;
    }

    // Give a host tool a short window to select TEST MODE before Wi-Fi setup
    // asks for credentials or the application waits for NTP.
    vTaskDelay(pdMS_TO_TICKS(1000));

    bool found_credentials = false;
    if (!load_credentials(&found_credentials)) {
        return false;
    }
    if (!found_credentials && !s_test_mode_active.load() && !prompt_for_credentials()) {
        return false;
    }
    if (!found_credentials && s_test_mode_active.load()) {
        ESP_LOGI(TAG, "TEST MODE selected; Wi-Fi credentials are not needed for camera test");
    }
    return initialize_network_stack();
}

bool wifi_manager_connect()
{
    if (!s_wifi_initialized.load() || !s_wifi_events) {
        return false;
    }
    face_display_show("CONNECTING WIFI", "WAITING FOR AP...", nullptr, nullptr);

    wifi_config_t config{};
    std::memcpy(config.sta.ssid, s_credentials.ssid, s_credentials.ssid_len);
    std::memcpy(config.sta.password, s_credentials.password,
                s_credentials.password_len);
    config.sta.threshold.authmode = WIFI_AUTH_OPEN;
    config.sta.pmf_cfg.capable = true;
    config.sta.pmf_cfg.required = false;

    s_wifi_had_ip.store(false);
    s_wifi_retry_count.store(0);
    s_connection_failed.store(false);
    xEventGroupClearBits(s_wifi_events, WIFI_CONNECTED_BIT | WIFI_FAILED_BIT);

    esp_err_t err = esp_wifi_set_mode(WIFI_MODE_STA);
    if (err == ESP_OK) {
        err = esp_wifi_set_config(WIFI_IF_STA, &config);
    }
    if (err == ESP_OK) {
        err = esp_wifi_start();
    }
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Could not start station mode: %s", esp_err_to_name(err));
        s_connection_failed.store(true);
        wifi_manager_stop();
        return false;
    }

    ESP_LOGI(TAG, "Connecting to configured 2.4 GHz Wi-Fi network (SSID hidden)");
    const EventBits_t bits = xEventGroupWaitBits(
        s_wifi_events, WIFI_CONNECTED_BIT | WIFI_FAILED_BIT, pdTRUE, pdFALSE,
        pdMS_TO_TICKS(FACE_WIFI_CONNECT_TIMEOUT_MS));
    if (bits & WIFI_CONNECTED_BIT) {
        s_connection_failed.store(false);
        return true;
    }

    if (bits & WIFI_FAILED_BIT) {
        ESP_LOGE(TAG, "Wi-Fi retries exhausted before DHCP assigned an address");
    } else {
        ESP_LOGE(TAG, "Timed out waiting for IP_EVENT_STA_GOT_IP after %d ms",
                 FACE_WIFI_CONNECT_TIMEOUT_MS);
    }
    s_connection_failed.store(true);
    wifi_manager_stop();
    return false;
}

void wifi_manager_stop()
{
    face_display_set_wifi_connected(false);
    if (!s_wifi_initialized.load()) {
        return;
    }
    s_wifi_stopping.store(true);
    const esp_err_t disconnect_err = esp_wifi_disconnect();
    if (disconnect_err != ESP_OK && disconnect_err != ESP_ERR_WIFI_NOT_STARTED) {
        ESP_LOGD(TAG, "esp_wifi_disconnect returned %s", esp_err_to_name(disconnect_err));
    }
    const esp_err_t stop_err = esp_wifi_stop();
    if (stop_err != ESP_OK && stop_err != ESP_ERR_WIFI_NOT_STARTED) {
        ESP_LOGW(TAG, "esp_wifi_stop returned %s", esp_err_to_name(stop_err));
    }
    s_wifi_had_ip.store(false);
    if (s_wifi_events) {
        xEventGroupClearBits(s_wifi_events, WIFI_CONNECTED_BIT | WIFI_FAILED_BIT);
    }
}

bool wifi_manager_recovery_requested()
{
    return s_reset_requested.load() || s_connection_failed.load();
}

bool wifi_manager_take_frame_request()
{
    return s_frame_requested.exchange(false);
}

bool wifi_manager_test_mode_active()
{
    return s_test_mode_active.load();
}

bool wifi_manager_ensure_time_synced()
{
    while (true) {
        if (s_credentials.ssid_len == 0 && !prompt_for_credentials()) {
            return false;
        }
        if (s_reset_requested.exchange(false)) {
            wifi_manager_stop();
            const esp_err_t err = erase_credential_keys();
            if (err != ESP_OK) {
                ESP_LOGE(TAG, "Could not erase saved credentials: %s", esp_err_to_name(err));
                return false;
            }
            std::memset(&s_credentials, 0, sizeof(s_credentials));
            if (!prompt_for_credentials()) {
                return false;
            }
        } else if (s_connection_failed.exchange(false)) {
            wifi_manager_stop();
            if (!read_recovery_choice()) {
                return false;
            }
        }

        if (!wifi_manager_connect()) {
            s_connection_failed.store(false);
            if (!read_recovery_choice()) {
                return false;
            }
            continue;
        }

        face_display_show("WIFI CONNECTED", "SYNCING TIME...", FACE_NTP_SERVER, nullptr);
        esp_sntp_config_t config = ESP_NETIF_SNTP_DEFAULT_CONFIG(FACE_NTP_SERVER);
        esp_err_t err = esp_netif_sntp_init(&config);
        if (err == ESP_OK) {
            err = esp_netif_sntp_sync_wait(pdMS_TO_TICKS(FACE_NTP_WAIT_MS));
            esp_netif_sntp_deinit();
        }
        wifi_manager_stop();

        const time_t now = std::time(nullptr);
        if (err == ESP_OK && now >= 1700000000) {
            if (s_reset_requested.load()) {
                continue;
            }
            ESP_LOGI(TAG, "Clock synchronized from %s", FACE_NTP_SERVER);
            face_display_show("WORK MODE", "WIFI CONNECTED", "TIME SYNCED", "FINDING FACE");
            s_connection_failed.store(false);
            return true;
        }
        ESP_LOGE(TAG, "NTP synchronization failed (%s); camera remains idle",
                 esp_err_to_name(err));
        face_display_show("TIME SYNC FAILED", "CHECK INTERNET", "RETRY OR RESET WIFI", nullptr);
        if (!read_recovery_choice()) {
            return false;
        }
    }
}
