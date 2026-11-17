#pragma once

#include <cstdint>

bool face_display_init();
void face_display_set_wifi_connected(bool connected);
void face_display_show(const char *line1, const char *line2 = nullptr,
                      const char *line3 = nullptr, const char *line4 = nullptr);
void face_display_show_camera_frame(const uint16_t *rgb565,
                                    uint16_t frame_width, uint16_t frame_height);
