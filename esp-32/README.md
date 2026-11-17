# F.A.C.E ESP32-CAM firmware

ESP-IDF firmware for the AI-Thinker ESP32-CAM (original ESP32, OV2640). It
uses the checked-out ESP-WHO detector and ESP-DL model libraries; it does not
perform identity matching or attendance processing on the device.

## Configuration

Wi-Fi credentials are entered in the serial monitor on first boot and saved
in NVS; they do not need to be compiled into the firmware. `face_config.h`
contains the server endpoint settings:

- Set `FACE_SERVER_HOST` to the laptop's LAN IPv4 address running
  `backend/esp-server.py`.
- Keep the Flask port at 5000 unless the server is changed.

The Flask server must expose `POST /upload` and accept a raw `image/jpeg`
request body. The firmware adds device, capture ID, timestamp, and resolution
headers. Capture IDs remain the same across the bounded HTTP retries.

## Build and flash

Use the ESP-IDF v5.5.6 environment and from this directory run:

```text
idf.py set-target esp32
idf.py build
idf.py -p COMx flash monitor
```

The 4 MB partition table leaves a 3.75 MiB application slot. The project is
configured for the AI-Thinker pin map and 4 MB PSRAM. Connect GPIO0 to GND only
while entering the ESP32-CAM bootloader; remove that connection before reset.
Wi-Fi's optional IRAM speed optimization is disabled to fit the original
ESP32's limited internal RAM; Wi-Fi is only active for NTP and image uploads.

## I2C OLED wiring

The firmware uses the ESP-IDF SSD1306 driver and assumes a 4-pin I2C OLED
(SSD1306-compatible, 128x64 by default). It scans addresses `0x3C` and `0x3D`.
For a 128x32 panel, set `FACE_OLED_HEIGHT` to `32` in `main/face_config.h`.

| OLED / supply | AI-Thinker ESP32-CAM |
| --- | --- |
| OLED VCC | 3V3 |
| OLED GND | GND |
| OLED SDA | GPIO13 |
| OLED SCL | GPIO14 |
| Micro-USB breakout VBUS / 5V | 5V |
| Micro-USB breakout GND | GND |

```text
Micro-USB breakout                 ESP32-CAM                 I2C OLED
  VBUS / +5V ---------------------- 5V
  GND ----------------------------- GND --------------------- GND
                                      3V3 -------------------- VCC
                                      GPIO13 ----------------- SDA
                                      GPIO14 ----------------- SCL
```

Use GPIO13/14 only when the microSD socket is not in use. Power the ESP32-CAM
through its `5V` pin and power the OLED from `3V3`, so the I2C lines stay at
3.3 V. Use a stable 5 V supply rated for at least 1 A. If a separate USB-UART
adapter is connected for flashing/serial, connect its GND, TX to GPIO3/U0R, and
RX to GPIO1/U0T; leave the adapter's 5V/VCC disconnected while the breakout
powers the board. Connect GPIO0 to GND only for flashing, then remove it before
normal boot.

The onboard white flash LED on GPIO4 is held off. GPIO4 is shared with the
microSD interface, so keep the card socket unused. The OLED output is rotated
180 degrees in firmware.

## Runtime behavior

- QVGA RGB565 frames feed ESP-WHO's two-stage MSR01/MNP01 face detector using
  the ESP-WHO ESP32 example thresholds and resize setting.
- One positive frame triggers a switch to UXGA JPEG capture. The loop has a
  15 FPS pacing target and reports its measured inference rate; the original
  ESP32 may not reach that target with the two-stage detector.
- Only the UXGA JPEG is posted. Wi-Fi is stopped after each upload attempt.
- After a successful upload, another capture requires the face to clear for ten
  frames and the 30-second cooldown to expire. A failed upload can be retried
  after its 30-second retry cooldown.
- SNTP time is required before camera operation. The clock uses IST; outside
  09:00–17:00 the device enters deep sleep until the next 09:00.

If SNTP is unavailable, the camera remains idle. The serial monitor provides
retry, new-credential, and reset options so Wi-Fi and clock recovery remain
available. At any time while the device is awake, type `wifi reset` and press
Enter to erase saved Wi-Fi credentials and enter replacements.

## Test and work modes

Work Mode is the default. It synchronizes time over Wi-Fi, triggers on one
positive face detection, and performs the existing UXGA capture/upload flow.
The QVGA camera uses two latest-frame buffers, and OLED preview refresh is
limited to 4 FPS to keep it from throttling inference.
The OLED keeps an IST clock and Wi-Fi status in its status bar, with state
messages centered in larger text. The 09:00–17:00 sleep schedule is temporarily disabled by
`FACE_ENFORCE_OPERATING_HOURS` in `main/face_config.h`.

Test Mode runs the camera without Wi-Fi, NTP, the operating-hours schedule, or
uploads. It prints MSR proposal and final face counts/scores and draws orange
proposal boxes and green confirmed-face boxes on the preview. Start the USB
viewer to select Test Mode automatically; pressing `q` or Esc switches back to
Work Mode. From a serial terminal, `mode test` and `mode work` also switch modes.
When returning to Work Mode, the firmware obtains Wi-Fi credentials if needed
and synchronizes time before resuming the schedule.

When the OLED is connected, it shows Wi-Fi association/IP, time sync, camera
state, face detection, UXGA capture, upload retries, and upload completion.
During Work Mode face search, it displays a locally downsampled monochrome
camera view at the detector's frame rate. On a face hit, the image is replaced
with a “FACE FOUND / STAY STABLE” message during final confirmation/capture.
This preview is rendered locally over I2C; it does not use Wi-Fi video. Missing
or unrecognized OLED hardware is logged and does not stop the camera.

## Serial setup and use

Open the serial monitor at 115200 baud. On first boot the firmware prompts for
the SSID and password; an empty password selects an open network. Password
characters are not echoed or logged. Later boots use the stored credentials.
Type `wifi reset` and press Enter while the device is awake to erase them and
run setup again. SSIDs and passwords are accepted as raw serial text, including
spaces and backslashes; SSIDs may be up to 32 bytes and passwords up to 64
bytes. CRLF and LF line endings are supported.

To run a live low-resolution detector test without Wi-Fi, close `idf.py monitor`
and run `python tools/serial_frame_viewer.py COMx`. The viewer restarts the
board, selects Test Mode, polls camera frames over USB, and overlays detector
status. Press `q` or Esc to restore Work Mode. Install viewer dependencies with
`python -m pip install pyserial opencv-python numpy`.
