#!/usr/bin/env python3

import os
import shutil
import fnmatch
import time
import json
import argparse
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from rich.progress import Progress, SpinnerColumn, BarColumn, TimeElapsedColumn
from rich.console import Console
from rich.table import Table

console = Console()


def sha256_file(path, chunk_size=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def write_log(log_path, level, message, source="", destination=""):
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": level,
        "message": message,
        "source": str(source),
        "destination": str(destination),
        "pid": os.getpid()
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def load_state(state_path):
    if Path(state_path).exists():
        with open(state_path, "r") as f:
            return json.load(f)
    return {"processed": [], "hashes": {}}


def save_state(state_path, state):
    with open(state_path, "w") as f:
        json.dump(state, f)

import sqlite3

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            hash TEXT,
            status TEXT
        )
    """)
    conn.commit()
    return conn

def matches_filters(path, include, exclude):
    name, full = path.name, str(path)

    if include and not any(fnmatch.fnmatch(name, p) or fnmatch.fnmatch(full, p) for p in include):
        return False

    if exclude and any(fnmatch.fnmatch(name, p) or fnmatch.fnmatch(full, p) for p in exclude):
        return False

    return True

def verify_checksum(src_hash, dst_path):
    if not dst_path.exists():
        return False
    return src_hash == sha256_file(dst_path)


def move_with_retry(item, dst, args, conn):
    cur = conn.cursor()
    src = item

    # Skip already processed
    cur.execute("SELECT status FROM files WHERE path=?", (str(src),))
    row = cur.fetchone()
    if row and row[0] == "moved":
        return "skipped"

    file_hash = sha256_file(src) if src.is_file() else None

    attempt = 0
    while attempt <= args.retry_count:
        try:
            if dst.exists() and not args.overwrite:
                return "conflict"

            shutil.move(str(src), str(dst))

            # VERIFY
            if file_hash and not verify_checksum(file_hash, dst):
                raise Exception("Checksum verification failed")

            cur.execute(
                "INSERT OR REPLACE INTO files VALUES (?, ?, ?)",
                (str(src), file_hash, "moved")
            )
            conn.commit()

            return "moved"

        except Exception as e:
            if attempt >= args.retry_count:
                write_log(args.log_path, "ERROR", str(e), src, dst)
                return "error"

            time.sleep(args.retry_delay / 1000)
            attempt += 1

def main():
    parser = argparse.ArgumentParser(description="Production directory flattener")
    parser.add_argument("--path", default=".")
    parser.add_argument("--include", nargs="*")
    parser.add_argument("--exclude", nargs="*")
    parser.add_argument("--max-depth", type=int, default=100)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--parallel", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--retry-count", type=int, default=3)
    parser.add_argument("--retry-delay", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--log-path", default="move.log")
    parser.add_argument("--state-path", default=".move_state.json")

    args = parser.parse_args()

    root = Path(args.path).resolve()
    state = load_state(args.state_path)

    items = [
        p for p in root.rglob("*")
        if p != root
        and (not p.is_dir())
        and len(p.relative_to(root).parts) <= args.max_depth
        and matches_filters(p, args.include, args.exclude)
    ]

    if not items:
        console.print("[yellow]No items found[/yellow]")
        return

    # Preview table
    table = Table(title="Planned Moves")
    table.add_column("Source")
    table.add_column("Destination")

    for i in items[:10]:
        table.add_row(str(i), str(root / i.name))

    console.print(table)

    if args.dry_run:
        console.print("[cyan]Dry run complete[/cyan]")
        return

    if not args.yes:
        if input("Proceed? (y/N): ").lower() != "y":
            return

    results = {"moved": 0, "conflict": 0, "duplicate": 0, "error": 0}

    with Progress(
        SpinnerColumn(),
        BarColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:

        task = progress.add_task("Processing...", total=len(items))

        def process(item):
            dst = root / item.name
            return move_with_retry(item, dst, args, state)

        if args.parallel:
            with ThreadPoolExecutor(max_workers=args.workers) as ex:
                futures = [ex.submit(process, i) for i in items]
                for f in as_completed(futures):
                    r = f.result()
                    if r in results:
                        results[r] += 1
                    progress.update(task, advance=1)
        else:
            for i in items:
                r = process(i)
                if r in results:
                    results[r] += 1
                progress.update(task, advance=1)

        save_state(args.state_path, state)

    # Summary table
    summary = Table(title="Summary")
    summary.add_column("Result")
    summary.add_column("Count")

    for k, v in results.items():
        summary.add_row(k, str(v))

    console.print(summary)
    console.print(f"[green]Log:[/green] {args.log_path}")
    console.print(f"[green]State:[/green] {args.state_path}")


if __name__ == "__main__":
    main()