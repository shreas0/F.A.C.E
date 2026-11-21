
from flask import Flask, request, jsonify
import numpy as np
import cv2
import os
import re
import uuid
import json

app = Flask(__name__)
ESP_SERVER_PORT = int(os.getenv("ESP_SERVER_PORT", "5001"))
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.getenv("FACE_ATTENDANCE_IMAGE_DIR", os.path.join(BACKEND_DIR, "attending_faces"))
os.makedirs(SAVE_DIR, exist_ok=True)

WIDTH = 320
HEIGHT = 240
FRAME_BYTES = WIDTH * HEIGHT * 2


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"service": "esp_api", "status": "ok"})


def _attendance_result_path(image_path):
    return image_path + ".attendance.json"


def _recognize_and_mark(image_path):
    """Run recognition once for this capture and persist its response for retries."""
    result_path = _attendance_result_path(image_path)
    if os.path.isfile(result_path):
        try:
            with open(result_path, "r", encoding="utf-8") as result_file:
                cached = json.load(result_file)
                # Only return cached result if it was a final business status, not a server/database error
                if cached.get("status") in ("marked", "already_marked") or cached.get("reason") in ("unknown", "no_face"):
                    return cached
        except (OSError, ValueError):
            pass
    try:
        # Lazy import keeps camera upload validation independent of ML startup.
        from recognition import process_image
        result = process_image(image_path)
    except Exception as exc:
        app.logger.exception("Recognition or attendance marking failed")
        result = {"status": "not_marked", "name": "", "reason": "recognition_error"}
    try:
        temporary_result = result_path + ".tmp"
        with open(temporary_result, "w", encoding="utf-8") as result_file:
            json.dump(result, result_file, ensure_ascii=False)
        os.replace(temporary_result, result_path)
    except OSError:
        app.logger.exception("Could not persist recognition result")
    return result


@app.route("/upload", methods=["POST"])
def upload_jpeg():
    """Save one JPEG posted by the ESP32-CAM firmware and recognize the face."""
    if request.mimetype != "image/jpeg":
        return jsonify({"error": "Content-Type must be image/jpeg"}), 415

    data = request.get_data(cache=False)
    if len(data) < 4 or not data.startswith(b"\xff\xd8") or not data.endswith(b"\xff\xd9"):
        return jsonify({"error": "Request body is not a complete JPEG"}), 400

    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        return jsonify({"error": "JPEG could not be decoded"}), 400
    width, height = image.shape[1], image.shape[0]
    if width < 160 or height < 120:
        return jsonify({"error": "Image resolution too low for face recognition",
                        "received": f"{width}x{height}"}), 400
    resolution_str = f"{width}x{height}"

    device_id = re.sub(r"[^A-Za-z0-9_-]", "_", request.headers.get("X-Device-ID", "esp32cam"))[:32]
    capture_id = re.sub(r"[^A-Za-z0-9_-]", "_", request.headers.get("X-Capture-ID", ""))[:64]
    if not capture_id:
        capture_id = uuid.uuid4().hex
    filename = f"facecam_{device_id}_{capture_id}.jpg"
    filepath = os.path.join(SAVE_DIR, filename)

    # Capture IDs are reused across firmware retries, making this endpoint
    # idempotent if the server saved an image but the reply was lost.
    if os.path.exists(filepath):
        attendance = _recognize_and_mark(filepath)
        return jsonify({"status": "success", "duplicate": True,
                        "file": filename, "resolution": resolution_str,
                        "attendance": attendance}), 200

    temporary_path = filepath + "." + uuid.uuid4().hex + ".tmp"
    try:
        with open(temporary_path, "wb") as image_file:
            image_file.write(data)
        os.replace(temporary_path, filepath)
    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)

    print(f"Saved JPEG ({resolution_str}) from {device_id}: {filename}")
    attendance = _recognize_and_mark(filepath)
    return jsonify({"status": "success", "file": filename,
                    "resolution": resolution_str,
                    "attendance": attendance,
                    "capture_timestamp": request.headers.get("X-Capture-Timestamp")}), 200


@app.route("/upload-batch", methods=["POST"])
def upload_batch():

    try:
        photo_count = int(request.headers.get("X-Photo-Count", 20))
        frame_bytes = int(request.headers.get("X-Frame-Bytes", FRAME_BYTES))

        if photo_count != 5 or frame_bytes != FRAME_BYTES:
            return jsonify({"error": "Unexpected batch configuration"}), 400

        data = request.get_data()

        expected_size = photo_count * frame_bytes

        if len(data) != expected_size:
            return jsonify({
                "error": "Incorrect batch size",
                "received": len(data),
                "expected": expected_size
            }), 400

        saved_files = []

        for i in range(photo_count):

            start = i * frame_bytes
            end = start + frame_bytes

            frame_data = data[start:end]

            pixels = np.frombuffer(frame_data, dtype=">u2")
            pixels = pixels.reshape((HEIGHT, WIDTH))

            r = ((pixels >> 11) & 0x1F) << 3
            g = ((pixels >> 5) & 0x3F) << 2
            b = (pixels & 0x1F) << 3

            rgb = np.stack(
                (r, g, b), axis=-1
            ).astype(np.uint8)

            image = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

            filename = f"photo_{i + 1:02d}.jpg"
            filepath = os.path.join(SAVE_DIR, filename)

            if not cv2.imwrite(filepath, image):
                raise RuntimeError(f"Failed to save {filename}")

            saved_files.append(filename)

        print(f"Successfully saved {len(saved_files)} photos.")

        return jsonify({
            "status": "success",
            "saved": len(saved_files),
            "folder": SAVE_DIR,
            "files": saved_files
        }), 200

    except Exception as e:
        print("Batch error:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=ESP_SERVER_PORT,
        debug=False,
        threaded=True
    )
