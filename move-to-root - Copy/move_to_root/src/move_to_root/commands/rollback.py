from pathlib import Path
import shutil
from ..db import get_db
from ..logging import log


def rollback(args):
    root = Path(args.path).resolve()
    conn = get_db(root)
    cur = conn.cursor()

    cur.execute("SELECT src, dst FROM moves ORDER BY id DESC")
    rows = cur.fetchall()

    if not rows:
        print("Nothing to rollback")
        return

    for src, dst in rows:
        dst_path = Path(dst)
        src_path = Path(src)

        if dst_path.exists():
            shutil.move(str(dst_path), str(src_path))

    cur.execute("DELETE FROM moves")
    conn.commit()
    conn.close()

    print("ROLLBACK COMPLETE")
    log(args, "INFO", "rollback started", mode="rollback")