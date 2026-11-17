idf_component_register(
    SRCS "app_main.cpp" "wifi_manager.cpp" "face_display.cpp"
    INCLUDE_DIRS "."
    REQUIRES
        esp-dl
        espressif__esp32-camera
        esp_event
        esp_http_client
        esp_lcd
        esp_netif
        esp_psram
        esp_driver_gpio
        esp_timer
        esp_wifi
        json
        nvs_flash
)
