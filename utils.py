import hashlib
import re

def hash_password(password):
    # Hash the password using MD5
    md5_hash = hashlib.md5(password.encode()).hexdigest()
    return md5_hash

def is_strong_password(password):
    min_length = 8

    if len(password) < min_length:
        return False

    return True