import hashlib
from pathlib import Path

def sha256_file(path: Path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def verify_move(src_hash, dst_path: Path):
    if not dst_path.exists():
        return False
    return sha256_file(dst_path) == src_hash