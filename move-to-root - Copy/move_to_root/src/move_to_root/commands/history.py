from pathlib import Path
from ..db import get_db


def history(args):
    root = Path(args.path).resolve()
    conn = get_db(root)
    cur = conn.cursor()

    cur.execute("""
        SELECT run_id, mode, timestamp
        FROM runs
        ORDER BY timestamp DESC
        LIMIT 20
    """)

    rows = cur.fetchall()

    print("\nHISTORY")
    print("-" * 40)

    for r in rows:
        print(f"{r[0]} | {r[1]} | {r[2]}")