import os
import sys
import time
import json
import numpy as np
from deepface import DeepFace

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database import Database

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
WATCH_FOLDERS = [os.path.join(BACKEND_DIR, "captured_faces")]
SIMILARITY_THRESHOLD = 0.40
POLL_INTERVAL = 2

for f in WATCH_FOLDERS:
    os.makedirs(f, exist_ok=True)

def get_cosine_distance(a, b):
    a, b = np.array(a), np.array(b)
    if a.size == 0 or b.size == 0 or a.shape != b.shape:
        raise ValueError("Face embeddings must have matching non-zero dimensions")
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    if denominator == 0:
        raise ValueError("Face embeddings must not be zero vectors")
    return 1.0 - (np.dot(a, b) / denominator)

def parse_encoding(enc):
    if isinstance(enc, (list, np.ndarray)):
        return enc
    try:
        return json.loads(enc)
    except Exception:
        return eval(enc)

def get_existing_students():
    try:
        rows = Database.read_all_students()
        existing = []
        for r in rows:
            s_id, name, enc = r[0], r[1], r[2]
            try:
                parsed = parse_encoding(enc)
                if not parsed or len(parsed) == 0:
                    continue
                existing.append({"id": s_id, "name": name, "encoding": parsed})
            except Exception:
                continue
        return existing
    except Exception as e:
        print(f"Database read error: {e}")
        return []

def register_from_image(image_path, user_name):
    time.sleep(0.3)
    try:
        embedding_objs = DeepFace.represent(
            img_path=image_path, model_name="Facenet", enforce_detection=False
        )
        if not embedding_objs:
            print(f"No face detected in {image_path}")
            return False
        new_embedding = embedding_objs[0]["embedding"]
    except Exception as e:
        print(f"Embedding error on {image_path}: {e}")
        return False

    existing_students = get_existing_students()

    for student in existing_students:
        if student["name"].strip().lower() == user_name.strip().lower():
            continue
        try:
            dist = get_cosine_distance(new_embedding, student["encoding"])
            if dist <= SIMILARITY_THRESHOLD:
                print(f"Already registered as '{student['name']}' (ID: {student['id']}), skipping {image_path}")
                return True
        except Exception:
            continue

    encoding_json = json.dumps(new_embedding if isinstance(new_embedding, list) else list(new_embedding))
    new_id = Database.create_student(user_name, encoding_json)

    if new_id:
        print(f"Successfully registered '{user_name}' (ID: {new_id}) in database from {image_path}")
    else:
        updated = Database.update_student_face_by_name(user_name, encoding_json)
        if updated:
            print(f"Successfully updated face encoding for '{user_name}' in database from {image_path}")
        else:
            print(f"Student '{user_name}' could not be registered.")

    return True

def process_folders():
    valid_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    for folder in WATCH_FOLDERS:
        if not os.path.exists(folder):
            continue
        for filename in os.listdir(folder):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in valid_exts:
                continue

            file_path = os.path.join(folder, filename)
            if not os.path.isfile(file_path):
                continue

            user_name = os.path.splitext(filename)[0]
            print(f"\nNew registration image found: {filename} for student '{user_name}'")
            processed = register_from_image(file_path, user_name)

            if processed:
                try:
                    os.remove(file_path)
                except Exception:
                    pass

if __name__ == "__main__":
    print(f"Watching {WATCH_FOLDERS} for new faces to register into Database... (Ctrl+C to stop)")
    try:
        while True:
            process_folders()
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        Database.close()
