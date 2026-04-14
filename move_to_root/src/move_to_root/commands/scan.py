from pathlib import Path
from collections import defaultdict

from rich.progress import Progress, SpinnerColumn, BarColumn, TimeElapsedColumn

from ..db import get_db
from ..hashing import sha256_file
from ..index import get_file_signature


def scan(args):
    root = Path(args.path).resolve()
    conn = get_db(root)
    cur = conn.cursor()

    files = [f for f in root.rglob("*") if f.is_file()]
    total = len(files)

    print(f"\nScanning: {root}")
    print(f"Total files: {total}\n")

    ext_counts = defaultdict(int)
    total_size = 0
    hash_map = defaultdict(list)

    # ------------------------
    # SINGLE STATUS BAR
    # ------------------------
    with Progress(
        SpinnerColumn(),
        BarColumn(),
        TimeElapsedColumn(),
    ) as progress:

        task = progress.add_task("Scanning files...", total=total)

        for f in files:
            size, mtime = get_file_signature(f)

            ext_counts[f.suffix.lower() or "no_ext"] += 1
            total_size += size

            # ------------------------
            # CACHE CHECK
            # ------------------------
            cur.execute(
                "SELECT size, mtime, hash FROM file_index WHERE path=?",
                (str(f),)
            )
            row = cur.fetchone()

            cached_hash = None

            if row and row[0] == size and row[1] == mtime:
                cached_hash = row[2]  # FAST PATH (reuse)
            elif args.check_duplicates:
                cached_hash = sha256_file(f)

            # ------------------------
            # UPDATE INDEX
            # ------------------------
            if args.check_duplicates:
                cur.execute("""
                    INSERT OR REPLACE INTO file_index (path, size, mtime, hash)
                    VALUES (?, ?, ?, ?)
                """, (str(f), size, mtime, cached_hash))

            # ------------------------
            # DUPLICATES
            # ------------------------
            if args.check_duplicates and cached_hash:
                hash_map[cached_hash].append(f)

            # ------------------------
            # PROGRESS UPDATE
            # ------------------------
            progress.advance(task)

    conn.commit()

    print("\nScan complete.")

    # ------------------------
    # SUMMARY
    # ------------------------
    if args.summary:
        print("\nSUMMARY")
        print("-" * 40)
        print(f"Total files: {total}")
        print(f"Total size: {round(total_size / (1024*1024), 2)} MB")

        print("\nFile types:")
        for ext, count in sorted(ext_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {ext}: {count}")

        # ------------------------
        # DUPLICATES
        # ------------------------
        if args.check_duplicates:
            print("\nDuplicates:")
            print("-" * 40)

            duplicates = {h: p for h, p in hash_map.items() if len(p) > 1}

            if not duplicates:
                print("No duplicates found.")
            else:
                for h, paths in duplicates.items():
                    print(f"\nHash: {h[:10]}...")
                    for p in paths:
                        print(f"  {p}")