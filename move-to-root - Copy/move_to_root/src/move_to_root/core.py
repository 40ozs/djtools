from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.progress import Progress
from move_to_root.hashing import sha256_file, verify_move
from move_to_root.db import init_db, record_move
from move_to_root.logging import log

import shutil
import time


def move_file(item, root, args, conn):
    dest = root / item.name

    if dest.exists() and not args.overwrite:
        return "conflict"

    for attempt in range(args.retry_count + 1):
        try:
            src_hash = sha256_file(item)

            shutil.move(str(item), str(dest))

            if not verify_move(src_hash, dest):
                raise Exception("Checksum mismatch")

            record_move(conn, item, src_hash)
            log(args, "INFO", f"moved {item}")
            return "moved"

        except Exception as e:
            if attempt >= args.retry_count:
                log(args, "ERROR", str(e))
                return "error"

            time.sleep(args.retry_delay / 1000)


def run(args):
    root = Path(args.path).resolve()
    conn = init_db()

    items = list(root.rglob("*"))
    items = [i for i in items if i.is_file()]

    with Progress() as progress:
        task = progress.add_task("Moving files", total=len(items))

        results = {"moved": 0, "conflict": 0, "error": 0}

        def worker(item):
            return move_file(item, root, args, conn)

        if args.parallel:
            with ThreadPoolExecutor(max_workers=args.workers) as ex:
                futures = [ex.submit(worker, i) for i in items]
                for f in as_completed(futures):
                    r = f.result()
                    if r in results:
                        results[r] += 1
                    progress.update(task, advance=1)
        else:
            for i in items:
                r = worker(i)
                if r in results:
                    results[r] += 1
                progress.update(task, advance=1)

    print(results)