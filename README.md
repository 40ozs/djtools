# djtools
Tools to help manage DJing. Files metadata sanitization, audio file management, etc


# Metadata Parser

## Audio Metadata Parser

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

CSV files are written using UTF‑8 encoding
If row or size limits are reached, additional files are created
All CSV parts from the same run share the same timestamp (when enabled)
Column names are generated dynamically from all extracted metadata keys

audio_metadata_part1_20260401_153012.csv

audio_metadata_part2_20260401_153012.csv

## Design Notes
ID3 frame extraction is applied to MP3 files only
CSV file size limits are approximate (filesystem-based)
Metadata values are converted to strings for CSV compatibility
Errors during extraction are captured per file and do not stop execution

