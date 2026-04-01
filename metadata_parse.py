#!/usr/bin/env python3
"""
metadata_parse.py

Purpose:
    Audio metadata scanner and CSV exporter.

    Recursively scans directories for supported audio files, extracts
    standard and extended metadata using mutagen, and exports results
    to one or more CSV files with configurable size limits.

Usage:
    python metadata_parse.py <path> [options]
    
    Run with --help to see available options.

Dependencies:
    - mutagen

Author:
    Denzel Walkes

Maintainer:
    Platform Engineering

Created:
    2026-04-01

Last Updated:
    ẅ̷̧̨̱̲̼̜̫͉́ẖ̶̨̨͖͚̘͍͍͓͇͎̤̹͉́̅̈́̉͑̇͘̕o̷͈̣̬̝͖̼͖̤̦̱̾̔ ̸̢̛͔̜̤̼̣͕͍̘̪͍̩̹͙̘̩̿̌̃͗k̴͓͕̼̏͐́n̵̛̹͙͈̝͚̼̮̦̾̌͐͛̊̈̂̒̈́͝ǫ̸̧̼̻͈̱̥͉̖̟̼͕̞̬͆̏́͊̀ͅw̵̗̯̤̯̗͉̲͓̔̅̀̄͊̂̎̌̈́̊s̷̢̖̏͋͂͑͌̀́̓̕̚



Notes:
    - CSV output is split to avoid size limits in common CSV readers
    - ID3 frame extraction is applied to MP3 files only


"""

import math
import os
import csv
from mutagen import File
from mutagen.id3 import ID3, ID3NoHeaderError

# Supported audio file extensions
AUDIO_EXTENSIONS = ('.mp3', '.flac', '.m4a', '.mp4', '.ogg', '.wav', '.aac')

# Ignores AppleDouble files or any other temp files
EXCLUDED_PREFIXES = ("._", ".", "~$")
EXCLUDED_FILES = ("thumbs.db", "desktop.ini")


def flatten_dict(d: dict, parent_key: str = '', sep: str = '.') -> dict:
    """
    Flatten a nested dictionary into a single-level dictionary.

    Nested keys are concatenated using the specified separator.

    Args:
        d: Dictionary to flatten.
        parent_key: Prefix for nested keys.
        sep: Separator used between key levels.

    Returns:
        Flattened dictionary with stringified values.
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, str(v)))
    return dict(items)


def is_valid_audio_file(filename: str) -> bool:
    """
    Checks the validity of files.
     
    Filters out temp and non-audio files are ignored

    Args:
        file: File name to evaluate.

    Returns:
        True if the file is a supported audio file.
    """
    lower = filename.lower()
    return (
        lower.endswith(AUDIO_EXTENSIONS)
        and not any(lower.startswith(p) for p in EXCLUDED_PREFIXES)
        and lower not in EXCLUDED_FILES
    )


def extract_metadata(file_path: str) -> dict:
    """"    
    Metadata collector for container information, tag metadata and extended ID3 frames.

    Args:
        file_path: Path to the audio file.

    Returns:
        Dictionary containing extracted metadata and error details
        when extraction fails.
    """
    metadata = {
        "file_path": file_path,
        "file_name": os.path.basename(file_path)
    }

    try:
        audio = File(file_path, easy=False)
        if audio is None:
            metadata["error"] = "Unsupported file"
            return metadata

        # Default tags 
        if audio.tags:
            for key in audio.tags.keys():
                try:
                    metadata[f"tag.{key}"] = str(audio.tags.get(key))
                except Exception as e:
                    metadata[f"tag.{key}"] = f"ERROR: {e}"

        # ID3 frames are only applicable to MP3 files
        if file_path.lower().endswith(".mp3"):
            try:
                id3 = ID3(file_path)
                for frame in id3.values():
                    frame_name = frame.FrameID
                    existing = metadata.get(f"id3.{frame_name}", "")
                    value = str(frame)

                    if existing:
                        metadata[f"id3.{frame_name}"] = existing + " | " + value
                    else:
                        metadata[f"id3.{frame_name}"] = value

            except ID3NoHeaderError:
                metadata["id3"] = "No ID3 header"

        # Basic information from the audio files
        if audio.info:
            metadata["info.length"] = getattr(audio.info, 'length', None)
            metadata["info.bitrate"] = getattr(audio.info, 'bitrate', None)
            metadata["info.sample_rate"] = getattr(audio.info, 'sample_rate', None)
            metadata["info.channels"] = getattr(audio.info, 'channels', None)

    except Exception as e:
        # Capture unexpected errors so processing can continue
        metadata["error"] = str(e)

    return metadata


def scan_directory(directory: str, ignore_dirs: list[str] | None = None) -> list:
    """
    Scan a directory recursively and extract metadata from audio files.

    Args:
        directory: Root directory to scan.
        ignore_dirs: Directory names to skip during traversal.

    Returns:
        List of metadata dictionaries.
    """
    all_data = []

    if ignore_dirs is None:
        ignore_dirs = []

    ignore_dirs = {d.lower() for d in ignore_dirs}

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d.lower() not in ignore_dirs]
        for file in files:
            if is_valid_audio_file(file):
                full_path = os.path.join(root, file)
                print(f"Processing: {full_path}")
                metadata = extract_metadata(full_path)
                all_data.append(metadata)

    return all_data


def write_csv_split(data, output_file, max_rows=50000, max_size_mb=None):
    """
    Write metadata records to one or more CSV files.

    CSV files are split when row or size limits are reached to
    maintain compatibility with common CSV readers.

    Args:
        data: Metadata records to write.
        output_file: Base output CSV filename.
        max_rows: Maximum rows per CSV file.
        max_size_mb: Approximate maximum file size per CSV in MB.

    """
    if not data:
        print("No data to write.")
        return

    all_keys = set()
    for row in data:
        all_keys.update(row.keys())
    all_keys = sorted(all_keys)

    base, ext = os.path.splitext(output_file)
    file_index = 1
    row_index = 0
    current_file = None
    writer = None

    def open_new_file(index):
        """Open a new CSV part file and write the header."""
        filename = f"{base}_part{index}{ext}"
        f = open(filename, "w", newline='', encoding="utf-8")
        w = csv.DictWriter(f, fieldnames=all_keys)
        w.writeheader()
        print(f"Writing: {filename}")
        return f, w, filename

    current_file, writer, current_filename = open_new_file(file_index)

    for row in data:
        writer.writerow(row)
        row_index += 1

        # Check row limit
        row_limit_reached = row_index >= max_rows

        # Check size limit (approx)
        size_limit_reached = False
        if max_size_mb:
            current_file.flush()
            # Approximate file size check (filesystem size, not CSV row size)
            size_mb = os.path.getsize(current_filename) / (1024 * 1024)
            size_limit_reached = size_mb >= max_size_mb

        if row_limit_reached or size_limit_reached:
            current_file.close()
            file_index += 1
            row_index = 0
            current_file, writer, current_filename = open_new_file(file_index)

    current_file.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Export audio metadata to CSV")
    parser.add_argument("path", help="Directory or file path")
    parser.add_argument("--output", "-o", default="audio_metadata.csv", help="Output CSV file")
    parser.add_argument("--ignore-dir", "-i", action="append", default=[], help="Add directories to ignore, must be added multiple times. (Optional)")
    parser.add_argument("--max-rows", "-r", type=int, default=50000, help="Max rows per CSV file (default: 50000)")
    parser.add_argument("--max-size-mb", "-s", type=int, default=None, help="Approx max file size in MB per CSV (Optional)")


    args = parser.parse_args()

    if os.path.isfile(args.path):
        # Single-file mode
        data = [extract_metadata(args.path)]
    else:
        # Directory scan mode
        data = scan_directory(args.path, ignore_dirs=args.ignore_dir)

    write_csv_split(data, args.output, max_rows=args.max_rows, max_size_mb=args.max_size_mb)

    print(f"\n✅ Metadata exported to {args.output}")