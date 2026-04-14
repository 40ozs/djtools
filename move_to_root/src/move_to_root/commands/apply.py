from pathlib import Path
import shutil

from ..db import get_db
from ..hashing import sha256_file
from ..utils import generate_run_id


def apply(args):
    root = Path(args.path).resolve()
    conn = get_db(root)
    cur = conn.cursor()

    run_id = generate_run_id()

    cur.execute(
        "INSERT INTO runs (run_id, mode, path) VALUES (?, ?, ?)",
        (run_id, "apply", str(root))
    )

    files = [f for f in root.rglob("*") if f.is_file()]

    for f in files:
        dst = root / f.name

        if dst.exists():
            continue

        file_hash = sha256_file(f)

        shutil.move(str(f), str(dst))

        cur.execute(
            "INSERT INTO moves (run_id, src, dst, hash) VALUES (?, ?, ?, ?)",
            (run_id, str(f), str(dst), file_hash)
        )

    conn.commit()
    conn.close()

    print(f"APPLY COMPLETE | run_id={run_id}")