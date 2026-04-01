import os
import csv
from mutagen import File
from mutagen.id3 import ID3, ID3NoHeaderError

AUDIO_EXTENSIONS = ('.mp3', '.flac', '.m4a', '.mp4', '.ogg', '.wav', '.aac')
EXCLUDED_PREFIXES = ("._", ".", "~$")
EXCLUDED_FILES = ("thumbs.db", "desktop.ini")


def flatten_dict(d, parent_key='', sep='.'):
    """Flatten nested dictionaries"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, str(v)))
    return dict(items)

def is_valid_audio_file(file):
    lower = file.lower()
    return (
        lower.endswith(AUDIO_EXTENSIONS)
        and not any(lower.startswith(p) for p in EXCLUDED_PREFIXES)
        and lower not in EXCLUDED_FILES
    )

def extract_metadata(file_path):
    metadata = {
        "file_path": file_path,
        "file_name": os.path.basename(file_path)
    }

    try:
        audio = File(file_path, easy=False)
        if audio is None:
            metadata["error"] = "Unsupported file"
            return metadata

        # --- Generic tags ---
        if audio.tags:
            for key in audio.tags.keys():
                try:
                    metadata[f"tag.{key}"] = str(audio.tags.get(key))
                except Exception as e:
                    metadata[f"tag.{key}"] = f"ERROR: {e}"

        # --- MP3 ID3 frames (extended tags) ---
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

        # --- Technical info ---
        if audio.info:
            metadata["info.length"] = getattr(audio.info, 'length', None)
            metadata["info.bitrate"] = getattr(audio.info, 'bitrate', None)
            metadata["info.sample_rate"] = getattr(audio.info, 'sample_rate', None)
            metadata["info.channels"] = getattr(audio.info, 'channels', None)

    except Exception as e:
        metadata["error"] = str(e)

    return metadata


def scan_directory(directory, ignore_dirs=None):
    all_data = []

    if ignore_dirs is None:
        ignore_dirs = []

    ignore_dirs = set(d.lower() for d in ignore_dirs)

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d.lower() not in ignore_dirs]
        for file in files:
            if is_valid_audio_file(file):
                full_path = os.path.join(root, file)
                print(f"Processing: {full_path}")
                metadata = extract_metadata(full_path)
                all_data.append(metadata)

    return all_data


def write_csv(data, output_file):
    # Collect all possible keys (columns)
    all_keys = set()
    for row in data:
        all_keys.update(row.keys())

    all_keys = sorted(all_keys)

    with open(output_file, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys)
        writer.writeheader()
        writer.writerows(data)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Export audio metadata to CSV")
    parser.add_argument("path", help="Directory or file path")
    parser.add_argument("--output", default="audio_metadata.csv", help="Output CSV file")
    parser.add_argument("--ignore-dir", action="append", default=[], help="Add directories to ignore, must be added multiple times.")

    args = parser.parse_args()

    if os.path.isfile(args.path):
        data = [extract_metadata(args.path)]
    else:
        data = scan_directory(args.path, ignore_dirs=args.ignore_dir)

    write_csv(data, args.output)

    print(f"\n✅ Metadata exported to {args.output}")