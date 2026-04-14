# djtools
Tools to help manage DJing. Files metadata sanitization, audio file management, etc


# Audio File Metadata Parser

A command-line tool for scanning audio files, extracting standard and extended metadata, and exporting the results to CSV.

The script recursively scans directories for supported audio formats, collects container information, tags, and extended ID3 metadata (MP3 only), and writes the output to one or more CSV files with configurable size limits.

---

## Features

- Supports common audio formats (`.mp3`, `.flac`, `.m4a`, `.wav`, `.ogg`, `.aac`, `.mp4`)
- Extracts:
  - Standard audio properties (length, bitrate, sample rate, channels)
  - Embedded tag metadata
  - Extended ID3 frames for MP3 files
- Recursively scans directories
- Skips system and temporary files
- Splits CSV output by row count and/or approximate file size
- Optional timestamped output filenames
- Fault-tolerant (continues processing even if individual files fail)

---

## Requirements

- Python 3.9+
- [`mutagen`](https://mutagen.readthedocs.io/)

Install dependencies:

```bash
pip install mutagen
```

## Usage
```bash
python metadata_parse.py <path> [options]
```
```bash
python metadata_parse.py --help
```
## Examples

Scan a directory and export metadata to the default CSV file:
```bash
python metadata_parse.py /path/to/audio
```

Disable timestamped filenames:
```bash
python metadata_parse.py /path/to/audio --no-timestamp
```

Scan a directory while ignoring specific subdirectories:
```bash
python metadata_parse.py /path/to/audio \
  --ignore-dir cache \
  --ignore-dir temp
```

Limit CSV output to 25,000 rows per file:
```bash
python metadata_parse.py /path/to/audio --max-rows 25000
```

Split CSV files by approximate size (in MB):
```bash
python metadata_parse.py /path/to/audio --max-size-mb 50
```

## Output

- CSV files are written using UTF‑8 encoding
- If row or size limits are reached, additional files are created
- All CSV parts from the same run share the same timestamp (when enabled)
- Column names are generated dynamically from all extracted metadata keys

File naming output
```bash
audio_metadata_part1_20260401_153012.csv
audio_metadata_part2_20260401_153012.csv
```
## Design Notes
ID3 frame extraction is applied to MP3 files only
CSV file size limits are approximate (filesystem-based)
Metadata values are converted to strings for CSV compatibility
Errors during extraction are captured per file and do not stop execution




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
```txt
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
```

### Tech Stack

| Component |	Technology |
| --------- | ---------- |
| Language |	Python 3.10+ |
| Database |	SQLite |
| CLI UI |	Rich |
| Audio Features |	Librosa |
| Hashing |	SHA256 |


