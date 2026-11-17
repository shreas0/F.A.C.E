import os
import sys
import time
import json
import threading
import numpy as np
from deepface import DeepFace

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database import Database

WATCH_FOLDERS = ["attending_face"]
SIMILARITY_THRESHOLD = 0.40
POLL_INTERVAL = 1
_recognition_lock = threading.Lock()

for f in WATCH_FOLDERS:
    os.makedirs(f, exist_ok=True)

def cosine_dist(a, b):
    a, b = np.array(a), np.array(b)
    return 1.0 - (np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def parse_encoding(enc):
    if isinstance(enc, (list, np.ndarray)):
        return enc
    try:
        return json.loads(enc)
    except Exception:
        return eval(enc)

def load_registered_students():
    try:
        rows = Database.read_all_students()
        students = []
        for r in rows:
            s_id, name, enc = r[0], r[1], r[2]
            try:
                parsed = parse_encoding(enc)
                students.append({"id": s_id, "name": name, "encoding": parsed})
            except Exception:
                continue
        return students
    except Exception as e:
        print(f"Error loading students from database: {e}")
        return []

def process_image(file_path):
    """Recognize the uploaded image and return an OLED-safe attendance result."""
    result = {"status": "not_marked", "name": "", "reason": "recognition_error"}
    # DeepFace and Database use process-wide resources; serialize requests.
    with _recognition_lock:
        try:
            emb_objs = DeepFace.represent(
                img_path=file_path, model_name="Facenet", enforce_detection=True
            )
            if not emb_objs:
                result["reason"] = "no_face"
                return result
            new_emb = emb_objs[0]["embedding"]
        except Exception as e:
            print(f"[ERROR] Could not scan face in {os.path.basename(file_path)}: {e}")
            result["reason"] = "no_face"
            return result

        students = load_registered_students()
        if not students:
            result["reason"] = "no_students"
            return result
        try:
            dists = [cosine_dist(new_emb, s["encoding"]) for s in students]
            idx = int(np.argmin(dists))
            min_dist = float(dists[idx])
        except Exception as e:
            print(f"[ERROR] Invalid student face encoding: {e}")
            result["reason"] = "database_error"
            return result
        if min_dist > SIMILARITY_THRESHOLD:
            print(f"[UNKNOWN] Face not recognized (Best Distance: {min_dist:.2f})")
            result["reason"] = "unknown"
            return result

        matched = students[idx]
        student_id, name = matched["id"], str(matched["name"])
        result.update({"name": name, "reason": "session_inactive"})
        print(f"[RECOGNIZED] Matched: {name} (Student ID: {student_id}, Distance: {min_dist:.2f})")
        try:
            if not Database.is_attendance_session_active():
                print("[SESSION] No active attendance session; attendance not marked.")
                return result
            att_id = Database.create_attendance(student_id, "present")
            if att_id:
                result.update({"status": "marked", "reason": ""})
                print(f"[ATTENDANCE] Marked {name} present (Record ID: {att_id})")
            elif Database.get_today_attendance_status(student_id) == "present":
                result.update({"status": "already_marked", "reason": ""})
                print(f"[DUPLICATE] {name} is already marked present today.")
            else:
                result["reason"] = "database_error"
        except Exception as e:
            print(f"[ERROR] Attendance database operation failed: {e}")
            result["reason"] = "database_error"
        return result

if __name__ == "__main__":
    students = load_registered_students()
    print(f"Loaded {len(students)} student(s) from Database.")
    print(f"Watching {WATCH_FOLDERS} for attendance images... (Ctrl+C to stop)\n")

    valid_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    try:
        while True:
            for folder in WATCH_FOLDERS:
                if not os.path.exists(folder):
                    continue
                for fname in os.listdir(folder):
                    if os.path.splitext(fname)[1].lower() in valid_exts:
                        fpath = os.path.join(folder, fname)
                        if os.path.isfile(fpath):
                            if not Database.is_attendance_session_active():
                                break
                            print(f"\nNew file detected: {fname}")
                            if process_image(fpath):
                                try:
                                    os.remove(fpath)
                                except Exception:
                                    pass
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\nWatcher stopped.")
    finally:
        Database.close()
