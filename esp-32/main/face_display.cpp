#include "face_display.h"

#include <algorithm>
#include <atomic>
#include <cctype>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <ctime>

#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "esp_err.h"
#include "esp_lcd_io_i2c.h"
#include "esp_lcd_panel_ops.h"
#include "esp_lcd_panel_ssd1306.h"
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

#include "face_config.h"

namespace {

constexpr char TAG[] = "face_display";
constexpr uint8_t DISPLAY_WIDTH = 128;
constexpr uint8_t DISPLAY_HEIGHT = FACE_OLED_HEIGHT;
constexpr uint8_t STATUS_HEIGHT = 8;
constexpr uint8_t IMAGE_HEIGHT = DISPLAY_HEIGHT - STATUS_HEIGHT;
constexpr size_t BUFFER_SIZE = DISPLAY_WIDTH * DISPLAY_HEIGHT / 8;

i2c_master_bus_handle_t s_i2c_bus = nullptr;
esp_lcd_panel_io_handle_t s_panel_io = nullptr;
esp_lcd_panel_handle_t s_panel = nullptr;
SemaphoreHandle_t s_mutex = nullptr;
bool s_ready = false;
std::atomic<bool> s_wifi_connected{false};
uint8_t s_pixels[BUFFER_SIZE]{};

esp_err_t flush_locked()
{
    if (!s_panel) return ESP_ERR_INVALID_STATE;
    const esp_err_t err = esp_lcd_panel_draw_bitmap(
        s_panel, 0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT, s_pixels);
    if (err != ESP_OK) {
        ESP_LOGD(TAG, "OLED update failed: %s", esp_err_to_name(err));
    }
    return err;
}

const uint8_t *glyph_for(char ch)
{
    static constexpr uint8_t letters[26][5] = {
        {0x7E,0x11,0x11,0x11,0x7E}, {0x7F,0x49,0x49,0x49,0x36},
        {0x3E,0x41,0x41,0x41,0x22}, {0x7F,0x41,0x41,0x22,0x1C},
        {0x7F,0x49,0x49,0x49,0x41}, {0x7F,0x09,0x09,0x09,0x01},
        {0x3E,0x41,0x49,0x49,0x7A}, {0x7F,0x08,0x08,0x08,0x7F},
        {0x00,0x41,0x7F,0x41,0x00}, {0x20,0x40,0x41,0x3F,0x01},
        {0x7F,0x08,0x14,0x22,0x41}, {0x7F,0x40,0x40,0x40,0x40},
        {0x7F,0x02,0x0C,0x02,0x7F}, {0x7F,0x04,0x08,0x10,0x7F},
        {0x3E,0x41,0x41,0x41,0x3E}, {0x7F,0x09,0x09,0x09,0x06},
        {0x3E,0x41,0x51,0x21,0x5E}, {0x7F,0x09,0x19,0x29,0x46},
        {0x46,0x49,0x49,0x49,0x31}, {0x01,0x01,0x7F,0x01,0x01},
        {0x3F,0x40,0x40,0x40,0x3F}, {0x1F,0x20,0x40,0x20,0x1F},
        {0x3F,0x40,0x38,0x40,0x3F}, {0x63,0x14,0x08,0x14,0x63},
        {0x07,0x08,0x70,0x08,0x07}, {0x61,0x51,0x49,0x45,0x43},
    };
    static constexpr uint8_t digits[10][5] = {
        {0x3E,0x51,0x49,0x45,0x3E}, {0x00,0x42,0x7F,0x40,0x00},
        {0x62,0x51,0x49,0x49,0x46}, {0x22,0x49,0x49,0x49,0x36},
        {0x18,0x14,0x12,0x7F,0x10}, {0x2F,0x49,0x49,0x49,0x31},
        {0x3E,0x49,0x49,0x49,0x32}, {0x01,0x71,0x09,0x05,0x03},
        {0x36,0x49,0x49,0x49,0x36}, {0x26,0x49,0x49,0x49,0x3E},
    };
    static constexpr uint8_t space[5] = {0,0,0,0,0};
    static constexpr uint8_t colon[5] = {0,0x36,0x36,0,0};
    static constexpr uint8_t period[5] = {0,0x60,0x60,0,0};
    static constexpr uint8_t dash[5] = {0x08,0x08,0x08,0x08,0x08};
    static constexpr uint8_t slash[5] = {0x20,0x10,0x08,0x04,0x02};
    static constexpr uint8_t bang[5] = {0,0,0x5F,0,0};
    static constexpr uint8_t question[5] = {0x02,0x01,0x51,0x09,0x06};

    const unsigned char upper = static_cast<unsigned char>(std::toupper(static_cast<unsigned char>(ch)));
    if (upper >= 'A' && upper <= 'Z') {
        return letters[upper - 'A'];
    }
    if (upper >= '0' && upper <= '9') {
        return digits[upper - '0'];
    }
    switch (upper) {
    case ':': return colon;
    case '.': return period;
    case '-': return dash;
    case '/': return slash;
    case '!': return bang;
    case '?': return question;
    default: return space;
    }
}

void set_pixel_locked(unsigned x, unsigned y)
{
    if (x >= DISPLAY_WIDTH || y >= DISPLAY_HEIGHT) {
        return;
    }
    s_pixels[x + (y / 8) * DISPLAY_WIDTH] |= 1U << (y % 8);
}

void draw_text_at(unsigned x, unsigned y, const char *text, unsigned scale = 1)
{
    if (!text || scale == 0) {
        return;
    }
    const unsigned advance = 5 * scale + 1;
    for (unsigned i = 0; text[i] && x + (i + 1) * advance <= DISPLAY_WIDTH; ++i) {
        const uint8_t *glyph = glyph_for(text[i]);
        for (unsigned col = 0; col < 5; ++col) {
            for (unsigned row = 0; row < 7; ++row) {
                if (glyph[col] & (1U << row)) {
                    for (unsigned dy = 0; dy < scale; ++dy) {
                        for (unsigned dx = 0; dx < scale; ++dx) {
                            set_pixel_locked(x + i * advance + col * scale + dx,
                                             y + row * scale + dy);
                        }
                    }
                }
            }
        }
    }
}

void draw_centered_text(const char *text, unsigned y, unsigned scale)
{
    if (!text) {
        return;
    }
    const unsigned advance = 5 * scale + 1;
    const size_t length = std::strlen(text);
    const unsigned count = std::min<unsigned>(static_cast<unsigned>(length),
                                               DISPLAY_WIDTH / advance);
    const unsigned width = count * advance;
    draw_text_at((DISPLAY_WIDTH - width) / 2, y, text, scale);
}

void draw_status_bar_locked()
{
    const unsigned top = DISPLAY_HEIGHT - STATUS_HEIGHT;
    std::memset(s_pixels + (top / 8) * DISPLAY_WIDTH, 0, DISPLAY_WIDTH);
    for (unsigned x = 0; x < DISPLAY_WIDTH; ++x) {
        set_pixel_locked(x, top);
    }

    char clock_text[8] = "--:--";
    const std::time_t now = std::time(nullptr);
    if (now >= 1704067200) {
        std::tm local{};
        if (localtime_r(&now, &local)) {
            std::snprintf(clock_text, sizeof(clock_text), "%02d:%02d",
                          local.tm_hour, local.tm_min);
        }
    }
    draw_text_at(1, top + 1, clock_text);
    const char *wifi_text = s_wifi_connected.load() ? "WIFI ON" : "WIFI OFF";
    const unsigned width = static_cast<unsigned>(std::strlen(wifi_text)) * 6;
    draw_text_at(DISPLAY_WIDTH - width - 1, top + 1, wifi_text);
}

void status_bar_task(void *)
{
    while (true) {
        vTaskDelay(pdMS_TO_TICKS(1000));
        if (s_ready && s_mutex && xSemaphoreTake(s_mutex, pdMS_TO_TICKS(50)) == pdTRUE) {
            draw_status_bar_locked();
            flush_locked();
            xSemaphoreGive(s_mutex);
        }
    }
}

} // namespace

bool face_display_init()
{
    if (s_ready) {
        return true;
    }
    static_assert(FACE_OLED_HEIGHT == 32 || FACE_OLED_HEIGHT == 64,
                  "SSD1306 height must be 32 or 64 pixels");
    s_mutex = xSemaphoreCreateMutex();
    if (!s_mutex) {
        ESP_LOGE(TAG, "Could not create display lock");
        return false;
    }

    struct PinCandidate {
        int sda;
        int scl;
        const char *label;
    };
    static const PinCandidate CANDIDATES[] = {
        {FACE_OLED_SDA_GPIO, FACE_OLED_SCL_GPIO, "Default (13/14)"},
        {FACE_OLED_SCL_GPIO, FACE_OLED_SDA_GPIO, "Reversed (14/13)"},
        {15, 14, "Alt (15/14)"},
        {14, 15, "Alt (14/15)"},
        {13, 15, "Alt (13/15)"},
        {15, 13, "Alt (15/13)"},
        {12, 13, "Alt (12/13)"},
        {13, 12, "Alt (13/12)"},
        {2, 14, "Alt (2/14)"},
        {14, 2, "Alt (14/2)"},
        {4, 13, "Alt (4/13)"},
        {13, 4, "Alt (13/4)"},
    };

    uint8_t address = 0x3C;
    int chosen_sda = FACE_OLED_SDA_GPIO;
    int chosen_scl = FACE_OLED_SCL_GPIO;
    bool found_device = false;

    for (const auto &cand : CANDIDATES) {
        // Bus recovery before probe to clear any stuck slave state
        gpio_set_direction(static_cast<gpio_num_t>(cand.sda), GPIO_MODE_INPUT_OUTPUT_OD);
        gpio_set_direction(static_cast<gpio_num_t>(cand.scl), GPIO_MODE_INPUT_OUTPUT_OD);
        gpio_set_pull_mode(static_cast<gpio_num_t>(cand.sda), GPIO_PULLUP_ONLY);
        gpio_set_pull_mode(static_cast<gpio_num_t>(cand.scl), GPIO_PULLUP_ONLY);
        gpio_set_level(static_cast<gpio_num_t>(cand.sda), 1);
        gpio_set_level(static_cast<gpio_num_t>(cand.scl), 1);
        esp_rom_delay_us(10);
        for (int i = 0; i < 9; ++i) {
            gpio_set_level(static_cast<gpio_num_t>(cand.scl), 0);
            esp_rom_delay_us(5);
            gpio_set_level(static_cast<gpio_num_t>(cand.scl), 1);
            esp_rom_delay_us(5);
        }

        i2c_master_bus_config_t bus_config{};
        bus_config.clk_source = I2C_CLK_SRC_DEFAULT;
        bus_config.i2c_port = I2C_NUM_0;
        bus_config.sda_io_num = static_cast<gpio_num_t>(cand.sda);
        bus_config.scl_io_num = static_cast<gpio_num_t>(cand.scl);
        bus_config.glitch_ignore_cnt = 7;
        bus_config.flags.enable_internal_pullup = true;

        i2c_master_bus_handle_t test_bus = nullptr;
        if (i2c_new_master_bus(&bus_config, &test_bus) == ESP_OK) {
            if (i2c_master_probe(test_bus, 0x3C, 50) == ESP_OK) {
                address = 0x3C;
                chosen_sda = cand.sda;
                chosen_scl = cand.scl;
                s_i2c_bus = test_bus;
                found_device = true;
                ESP_LOGI(TAG, "OLED detected on %s SDA=%d SCL=%d at 0x3C", cand.label, chosen_sda, chosen_scl);
                break;
            } else if (i2c_master_probe(test_bus, 0x3D, 50) == ESP_OK) {
                address = 0x3D;
                chosen_sda = cand.sda;
                chosen_scl = cand.scl;
                s_i2c_bus = test_bus;
                found_device = true;
                ESP_LOGI(TAG, "OLED detected on %s SDA=%d SCL=%d at 0x3D", cand.label, chosen_sda, chosen_scl);
                break;
            }
            i2c_del_master_bus(test_bus);
        }
    }

    if (!found_device) {
        ESP_LOGW(TAG, "No OLED ACKed during scan; driving configured breadboard SDA=%d SCL=%d at 0x3C",
                 FACE_OLED_SDA_GPIO, FACE_OLED_SCL_GPIO);
        i2c_master_bus_config_t bus_config{};
        bus_config.clk_source = I2C_CLK_SRC_DEFAULT;
        bus_config.i2c_port = I2C_NUM_0;
        bus_config.sda_io_num = static_cast<gpio_num_t>(FACE_OLED_SDA_GPIO);
        bus_config.scl_io_num = static_cast<gpio_num_t>(FACE_OLED_SCL_GPIO);
        bus_config.glitch_ignore_cnt = 7;
        bus_config.flags.enable_internal_pullup = true;
        esp_err_t b_err = i2c_new_master_bus(&bus_config, &s_i2c_bus);
        if (b_err != ESP_OK) {
            ESP_LOGE(TAG, "I2C bus init failed on SDA=%d SCL=%d: %s",
                     FACE_OLED_SDA_GPIO, FACE_OLED_SCL_GPIO, esp_err_to_name(b_err));
            return false;
        }
        address = 0x3C;
        chosen_sda = FACE_OLED_SDA_GPIO;
        chosen_scl = FACE_OLED_SCL_GPIO;
    }

    esp_lcd_panel_io_i2c_config_t io_config{};
    io_config.dev_addr = address;
    io_config.control_phase_bytes = 1;
    io_config.dc_bit_offset = 6;
    io_config.lcd_cmd_bits = 8;
    io_config.lcd_param_bits = 8;
    io_config.scl_speed_hz = 100000; // 100 kHz is much more noise-tolerant on breadboard jumpers
    io_config.transaction_timeout_ms = 1000;
    esp_err_t err = esp_lcd_new_panel_io_i2c(s_i2c_bus, &io_config, &s_panel_io);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "OLED I2C interface init failed: %s", esp_err_to_name(err));
        return false;
    }

    esp_lcd_panel_ssd1306_config_t oled_config{};
    oled_config.height = FACE_OLED_HEIGHT;
    esp_lcd_panel_dev_config_t panel_config{};
    panel_config.reset_gpio_num = -1;
    panel_config.bits_per_pixel = 1;
    panel_config.vendor_config = &oled_config;
    err = esp_lcd_new_panel_ssd1306(s_panel_io, &panel_config, &s_panel);
    if (err == ESP_OK) {
        esp_lcd_panel_reset(s_panel);
        esp_lcd_panel_init(s_panel);
        esp_lcd_panel_mirror(s_panel, true, true);
        esp_lcd_panel_disp_on_off(s_panel, true);
    } else {
        ESP_LOGW(TAG, "SSD1306 panel attach warning: %s (continuing for breadboard)", esp_err_to_name(err));
    }

    s_ready = true;
    ESP_LOGI(TAG, "SSD1306 OLED initialized (ready=true): 128x%d, I2C 0x%02X, SDA=%d SCL=%d",
             FACE_OLED_HEIGHT, address, FACE_OLED_SDA_GPIO, FACE_OLED_SCL_GPIO);
    face_display_show("FACE ATTENDANCE", "DISPLAY READY", "BOOTING...", nullptr);
    if (xTaskCreate(status_bar_task, "oled_status", 3072, nullptr, 1, nullptr) != pdPASS) {
        ESP_LOGE(TAG, "Could not start OLED clock/status task");
    }
    return true;
}

void face_display_set_wifi_connected(bool connected)
{
    s_wifi_connected.store(connected);
}

void face_display_show(const char *line1, const char *line2,
                       const char *line3, const char *line4)
{
    if (!s_ready || !s_mutex || xSemaphoreTake(s_mutex, portMAX_DELAY) != pdTRUE) {
        return;
    }
    std::memset(s_pixels, 0, sizeof(s_pixels));
    const char *lines[] = {line1, line2, line3, line4};
    unsigned count = 0;
    size_t longest = 0;
    for (const char *line : lines) {
        if (line && line[0]) {
            ++count;
            longest = std::max(longest, std::strlen(line));
        }
    }
    const unsigned scale = DISPLAY_HEIGHT >= 64 && count <= 3 && longest <= 11 ? 2 : 1;
    const unsigned line_height = 7 * scale + (scale == 1 ? 1 : 2);
    const unsigned content_height = count == 0 ? 0 : count * line_height - (scale == 1 ? 1 : 2);
    unsigned y = content_height < IMAGE_HEIGHT ? (IMAGE_HEIGHT - content_height) / 2 : 0;
    for (const char *line : lines) {
        if (line && line[0]) {
            draw_centered_text(line, y, scale);
            y += line_height;
        }
    }
    draw_status_bar_locked();
    flush_locked();
    xSemaphoreGive(s_mutex);
}

void face_display_show_camera_frame(const uint16_t *rgb565,
                                    uint16_t frame_width, uint16_t frame_height)
{
    if (!s_ready || !rgb565 || frame_width == 0 || frame_height == 0 || !s_mutex ||
        xSemaphoreTake(s_mutex, portMAX_DELAY) != pdTRUE) {
        return;
    }

    std::memset(s_pixels, 0, sizeof(s_pixels));
    uint32_t draw_width = DISPLAY_WIDTH;
    uint32_t draw_height = IMAGE_HEIGHT;
    if (static_cast<uint32_t>(frame_width) * IMAGE_HEIGHT >
        static_cast<uint32_t>(frame_height) * DISPLAY_WIDTH) {
        draw_height = static_cast<uint32_t>(frame_height) * DISPLAY_WIDTH / frame_width;
    } else {
        draw_width = static_cast<uint32_t>(frame_width) * IMAGE_HEIGHT / frame_height;
    }
    draw_width = std::max<uint32_t>(1, draw_width);
    draw_height = std::max<uint32_t>(1, draw_height);
    const uint32_t x_offset = (DISPLAY_WIDTH - draw_width) / 2;
    const uint32_t y_offset = (IMAGE_HEIGHT - draw_height) / 2;

    static constexpr uint8_t bayer[4][4] = {
        {0, 8, 2, 10}, {12, 4, 14, 6}, {3, 11, 1, 9}, {15, 7, 13, 5},
    };
    for (uint32_t y = 0; y < draw_height; ++y) {
        const uint32_t source_y = ((2 * y + 1) * frame_height) / (2 * draw_height);
        for (uint32_t x = 0; x < draw_width; ++x) {
            // Mirror only the live image horizontally for a selfie-style preview.
            const uint32_t mirrored_x = draw_width - 1 - x;
            const uint32_t source_x = ((2 * mirrored_x + 1) * frame_width) /
                                      (2 * draw_width);
            const uint16_t pixel = rgb565[source_y * frame_width + source_x];
            const uint32_t red = ((pixel >> 11) & 0x1F) * 255 / 31;
            const uint32_t green = ((pixel >> 5) & 0x3F) * 255 / 63;
            const uint32_t blue = (pixel & 0x1F) * 255 / 31;
            const uint32_t luminance = (77 * red + 150 * green + 29 * blue) >> 8;
            const uint32_t threshold = bayer[y & 3][x & 3] * 16 + 8;
            if (luminance > threshold) {
                const uint32_t display_x = x + x_offset;
                const uint32_t display_y = y + y_offset;
                s_pixels[display_x + (display_y / 8) * DISPLAY_WIDTH] |=
                    1U << (display_y % 8);
            }
        }
    }

    draw_status_bar_locked();
    flush_locked();
    xSemaphoreGive(s_mutex);
}
