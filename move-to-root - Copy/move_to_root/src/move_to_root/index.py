import os
from pathlib import Path
from .db import get_db
from .hashing import sha256_file


def get_file_signature(file: Path):
    stat = file.stat()
    return stat.st_size, stat.st_mtime