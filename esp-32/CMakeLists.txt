cmake_minimum_required(VERSION 3.16)

# Use the ESP-DL component from the local ESP-WHO checkout. Its prebuilt model
# libraries include the original ESP32 target and match the installed ESP-IDF.
set(EXTRA_COMPONENT_DIRS "C:/Espressif/esp-who/components/esp-dl")

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(face_firmware)
