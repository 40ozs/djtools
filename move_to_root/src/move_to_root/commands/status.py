from pathlib import Path
from ..db import get_db


def status(args):
    root = Path(args.path).resolve()
    conn = get_db(root)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM moves")
    move_count = cur.fetchone()[0]

    cur.execute("SELECT run_id, mode, timestamp FROM runs ORDER BY timestamp DESC LIMIT 1")
    last_run = cur.fetchone()

    print("\nSTATUS")
    print("-" * 40)

    print(f"Root: {root}")
    print(f"Total moves recorded: {move_count}")

    if last_run:
        print(f"Last run ID: {last_run[0]}")
        print(f"Mode: {last_run[1]}")
        print(f"Time: {last_run[2]}")