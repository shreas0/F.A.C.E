import os
import sys
import time
import json
import numpy as np
from deepface import DeepFace

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database import Database

WATCH_FOLDERS = ["attending_face", "attending_faces"]
SIMILARITY_THRESHOLD = 0.40
POLL_INTERVAL = 1

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
    if not Database.is_attendance_session_active():
        print("[SESSION] No active attendance session; skipping image.")
        return True
    time.sleep(0.3)
    try:
        emb_objs = DeepFace.represent(img_path=file_path, model_name="Facenet", enforce_detection=False)
        new_emb = emb_objs[0]["embedding"]
    except Exception as e:
        print(f"[ERROR] Could not scan face in {os.path.basename(file_path)}: {e}")
        return True

    students = load_registered_students()
    if not students:
        print("[WARNING] No registered students found in database.")
        return True

    dists = [cosine_dist(new_emb, s["encoding"]) for s in students]
    min_dist = min(dists)

    if min_dist <= SIMILARITY_THRESHOLD:
        idx = dists.index(min_dist)
        matched = students[idx]
        student_id = matched["id"]
        name = matched["name"]

        print(f"[RECOGNIZED] Matched: {name} (Student ID: {student_id}, Distance: {min_dist:.2f})")

        att_id = Database.create_attendance(student_id, "present")
        if att_id:
            print(f"[ATTENDANCE] Marked {name} (ID: {student_id}) as 'present' in Database (Record ID: {att_id})")
        else:
            print(f"[DUPLICATE] {name} (ID: {student_id}) is already marked present today.")
    else:
        print(f"[UNKNOWN] Face not recognized (Best Distance: {min_dist:.2f})")

    return True

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
