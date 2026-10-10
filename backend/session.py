
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database import Database


def main():
    print("Attendance session controller ready. Enter 1 to start or 0 to stop.")
    try:
        while True:
            choice = input("Session (1=start, 0=stop): ").strip()
            if choice == "1":
                session_id = Database.start_attendance_session()
                print(f"Attendance session {session_id} is active.")
            elif choice == "0":
                if Database.end_attendance_session():
                    print("Attendance session stopped.")
                else:
                    print("There is no active attendance session.")
            else:
                print("Enter 1 to start or 0 to stop.")
    except (KeyboardInterrupt, EOFError):
        print("\nSession controller stopped.")
    finally:
        Database.close()


if __name__ == "__main__":
    main()
