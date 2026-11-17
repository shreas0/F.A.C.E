#!/usr/bin/env python3
"""Show a continuous low-rate QVGA preview by polling frames over USB serial."""

import base64
import binascii
import os
import sys
import time

try:
    import cv2
    import numpy as np
    import serial
except ImportError as error:
    raise SystemExit(f"Missing preview dependency ({error.name}); install with: python -m pip install pyserial opencv-python numpy")


BAUD = 115200
WINDOW_TEST = "F.A.C.E. TEST MODE: live QVGA over USB — q returns to work mode"
WINDOW_WORK = "F.A.C.E. WORK MODE: live QVGA over USB — q closes preview"


def main() -> int:
    if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] != "--work"):
        print("Usage: python serial_frame_viewer.py COMx [--work]")
        return 2

    port = sys.argv[1]
    work_mode = len(sys.argv) == 3
    window = WINDOW_WORK if work_mode else WINDOW_TEST
    print(f"Opening {port} at {BAUD} baud. Close idf.py monitor first.")
    print("Frames are requested repeatedly over USB serial; no Wi-Fi video is used.")
    try:
        device = serial.Serial()
        device.port = port
        device.baudrate = BAUD
        device.timeout = 0.25
        device.dtr = False
        device.rts = False
        with device:
            time.sleep(0.1)
            device.rts = True
            time.sleep(0.1)
            device.rts = False
            time.sleep(0.5)
            device.write(b"mode work\r\n" if work_mode else b"mode test\r\n")
            device.flush()
            print(f"Selecting {'WORK' if work_mode else 'TEST'} MODE, then waiting for camera startup...")
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                raw = device.readline()
                if work_mode and raw and b"face_firmware:" in raw:
                    print(raw.decode("ascii", errors="replace").strip(), flush=True)
                if raw and b"Detection active:" in raw:
                    if work_mode:
                        print("WORK MODE: detection and uploads are active; q closes preview.")
                    else:
                        print("TEST MODE: detector diagnostics on, uploads disabled; q returns to WORK MODE.")
                    device.write(b"frame\r\n")
                    device.flush()
                    break
            else:
                print("Timed out waiting for detection. Check the board is awake and within 9 AM–5 PM IST.")
                return 1

            cv2.namedWindow(window, cv2.WINDOW_NORMAL)
            expected = None
            chunks = []
            last_frame_time = time.monotonic()
            frame_count = 0
            last_status = time.monotonic()
            face_status = "WORK MODE: finding face" if work_mode else "waiting for detector"
            latest_frame_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "build", "facecam_live_latest.jpg")
            )
            last_saved_frame = 0.0
            while True:
                raw = device.readline()
                if raw:
                    line = raw.decode("ascii", errors="ignore").strip()
                    if work_mode and line and not line.startswith("FACE_FRAME_"):
                        print(line, flush=True)
                    if "TEST MODE (uploads disabled):" in line:
                        face_status = line.split("TEST MODE (uploads disabled):", 1)[1].strip()
                    elif work_mode and "Face detected in one frame; starting capture" in line:
                        face_status = "FACE FOUND: starting capture"
                    elif work_mode and "Camera init failed:" in line:
                        face_status = "CAPTURE FAILED: camera init"
                    elif work_mode and "UXGA RGB565 capture invalid" in line:
                        face_status = "CAPTURE FAILED: invalid frame"
                    elif work_mode and "Could not encode UXGA" in line:
                        face_status = "CAPTURE FAILED: JPEG encode"
                    elif work_mode and "Starting image transfer:" in line:
                        face_status = "SENDING IMAGE"
                    elif work_mode and "JPEG uploaded (" in line:
                        face_status = "UPLOAD SUCCESS"
                    elif work_mode and "Upload attempt" in line and "failed" in line:
                        face_status = "UPLOAD FAILED: retrying"
                    elif work_mode and "Upload did not complete" in line:
                        face_status = "UPLOAD FAILED"
                    elif line.startswith("FACE_FRAME_BEGIN:"):
                        try:
                            _, length, width, height = line.split(":", 3)
                            expected = (int(length), int(width), int(height))
                            chunks.clear()
                        except ValueError:
                            expected = None
                    elif line.startswith("FACE_FRAME_DATA:") and expected:
                        chunks.append(line[len("FACE_FRAME_DATA:"):])
                    elif line == "FACE_FRAME_END" and expected:
                        length, width, height = expected
                        expected = None
                        try:
                            jpeg = base64.b64decode("".join(chunks), validate=True)
                        except (binascii.Error, ValueError):
                            chunks.clear()
                            print("Skipped a damaged serial frame; requesting another.")
                            device.write(b"frame\r\n")
                            device.flush()
                            continue
                        chunks.clear()
                        if len(jpeg) == length and jpeg.startswith(b"\xff\xd8") and jpeg.endswith(b"\xff\xd9"):
                            image = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
                            if image is not None:
                                now = time.monotonic()
                                fps = 1.0 / max(now - last_frame_time, 1e-6)
                                last_frame_time = now
                                frame_count += 1
                                cv2.putText(image, f"{'WORK' if work_mode else 'TEST'}: {face_status}",
                                            (5, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.40,
                                            (0, 255, 0), 1, cv2.LINE_AA)
                                cv2.putText(image, f"{width}x{height}  {fps:.1f} fps  USB",
                                            (5, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.40,
                                            (0, 255, 0), 1, cv2.LINE_AA)
                                cv2.imshow(window, image)
                                if now - last_saved_frame >= 1.0:
                                    cv2.imwrite(latest_frame_path, image)
                                    last_saved_frame = now
                                device.write(b"frame\r\n")
                                device.flush()
                                if now - last_status >= 5:
                                    print(f"Preview running: {frame_count} frames, {fps:.1f} fps")
                                    last_status = now

                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break

            try:
                device.write(b"mode work\r\n")
                device.flush()
            except serial.SerialException:
                pass
            cv2.destroyAllWindows()
            print("Preview stopped; WORK MODE restored.")
            return 0
    except serial.SerialException as error:
        print(f"Could not open {port}: {error}")
        return 1
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    raise SystemExit(main())
