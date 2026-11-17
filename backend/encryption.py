import os

from cryptography.fernet import Fernet


def generate_key():
    return Fernet.generate_key().decode("ascii")


def _cipher():
    key = os.getenv("FACE_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("Set FACE_ENCRYPTION_KEY before using encryption")
    return Fernet(key.encode("ascii"))


def encrypt_text(value):
    return _cipher().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_text(value):
    return _cipher().decrypt(value.encode("ascii")).decode("utf-8")
