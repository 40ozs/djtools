import sqlite3
from pathlib import Path

DB_NAME = ".move_to_root.db"


def get_db(root: Path):
    conn = sqlite3.connect(root / DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY,
        mode TEXT,
        path TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS moves (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT,
        src TEXT,
        dst TEXT,
        hash TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS file_index (
        path TEXT PRIMARY KEY,
        size INTEGER,
        mtime REAL,
        hash TEXT,
        artist TEXT,
        title TEXT,
        duration REAL,
        mime TEXT,
        embedding BLOB,
        last_scanned DATETIME
            )
    """)
    

    conn.commit()
    return conn