import hashlib
import hmac
import secrets


ITERATIONS = 600_000


def hash_password(password):
    salt = secrets.token_bytes(16)
    password_bytes = password.encode("utf-8")
    digest = hashlib.pbkdf2_hmac("sha256", password_bytes, salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password, stored_hash):
    try:
        algorithm, iterations, salt_hex, expected_digest = stored_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False

        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        ).hex()
        return hmac.compare_digest(actual_digest, expected_digest)
    except (AttributeError, TypeError, ValueError):
        return False
