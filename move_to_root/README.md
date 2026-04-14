# Move Items To Root (Python)

A high-performance filesystem intelligence engine for incremental indexing, duplicate detection, and audio-aware similarity search.

Supports:
- Incremental filesystem scanning (SQLite-backed)
- Duplicate detection via cryptographic hashing
- Cached metadata indexing for large directories
- Multi-stage audio similarity retrieval engine
- Structured CLI outputs for analysis and automation

---

## Features

### Core Capabilities
- Move all files from nested directories into root
- Recursive directory traversal
- Incremental scan using file metadata (size + mtime)
- SQLite-backed index to avoid redundant work

### Duplicate Detection Engine
- SHA256 file hashing
- Cached hash reuse for unchanged files
- Grouping of duplicate files by fingerprint

### Performance
- Multi-threaded execution
- Incremental updates instead of full rescans
- Optional deep scan mode (hash + metadata)

### Observability
- NDJSON logs (SIEM-ready)
- Structured state tracking

---

##  Requirements

- Python 3.9+
- Requirements:
```txt
rich 
numpy
soundfile
librosa
```

## Usage 

### CLI Run
```bash
move-to-root scan --path <dir> [--summary] [--check-duplicates]
move-to-root find-similar <file> --path <dir> [--threshold 0.85]
move-to-root apply
move-to-root rollback
move-to-root status
```

## Example Output

### Scan Output
```txt

Scanning: D:\Music
Total files: 34033

Scan complete.

SUMMARY
----------------------------------------
Total files: 34033
Total size: 18.4 GB

File types:
  .mp3: 12000
  .flac: 8000
  .wav: 4000
```

### Duplicate Detection
```txt
Duplicates:
----------------------------------------
Hash: a3f91c2d...
  track1.mp3
  track1_copy.mp3
```

### Similary Search
```txt

Target: song.mp3

SIMILAR FILES
----------------------------------------
0.94 → remix/song_remix.mp3
0.89 → live/song_live.mp3
0.86 → archive/song_old.mp3

```


## Architecture Overview
CLI Layer
   ↓
Command Layer (scan / apply / similarity)
   ↓
Core Engine
   ├── Scanner (filesystem traversal)
   ├── Indexer (SQLite)
   ├── Hasher (SHA256)
   ├── Audio Engine (features + embeddings)
   ↓
Storage Layer
   └── SQLite file index (incremental cache)

### Tech Stack

| Component |	Technology |
| --------- | ---------- |
| Language |	Python 3.10+ |
| Database |	SQLite |
| CLI UI |	Rich |
| Audio Features |	Librosa |
| Hashing |	SHA256 |

