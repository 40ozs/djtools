from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any

import numpy as np

# Optional imports (graceful degradation)
try:
    import librosa
    HAS_LIBROSA = True
except Exception:
    HAS_LIBROSA = False

try:
    import openl3
    import soundfile as sf
    HAS_OPENL3 = True
except Exception:
    HAS_OPENL3 = False


# =========================================================
# DATA MODEL
# =========================================================

@dataclass
class AudioFeatures:
    path: str
    size: int
    mtime: float

    duration: Optional[float] = None
    bitrate: Optional[int] = None

    chroma: Optional[np.ndarray] = None
    mfcc: Optional[np.ndarray] = None
    embedding: Optional[np.ndarray] = None


# =========================================================
# SQLITE INDEX LAYER
# =========================================================

class AudioIndex:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(db_path)
        self.cur = self.conn.cursor()
        self._init()

    def _init(self):
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS file_index (
            path TEXT PRIMARY KEY,
            size INTEGER,
            mtime REAL,
            duration REAL,
            bitrate INTEGER,
            chroma BLOB,
            mfcc BLOB,
            embedding BLOB
        )
        """)
        self.conn.commit()

    def get(self, path: str):
        self.cur.execute("SELECT * FROM file_index WHERE path=?", (path,))
        return self.cur.fetchone()

    def upsert(self, f: AudioFeatures):
        self.cur.execute("""
        INSERT OR REPLACE INTO file_index
        (path, size, mtime, duration, bitrate, chroma, mfcc, embedding)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f.path,
            f.size,
            f.mtime,
            f.duration,
            f.bitrate,
            _pack(f.chroma),
            _pack(f.mfcc),
            _pack(f.embedding)
        ))
        self.conn.commit()


# =========================================================
# SERIALIZATION HELPERS
# =========================================================

def _pack(arr: Optional[np.ndarray]):
    if arr is None:
        return None
    return arr.tobytes()

def _unpack(blob: Optional[bytes]):
    if blob is None:
        return None
    return np.frombuffer(blob, dtype=np.float32)


# =========================================================
# FEATURE EXTRACTION
# =========================================================

def extract_metadata(path: Path) -> Dict[str, Any]:
    stat = path.stat()
    return {
        "size": stat.st_size,
        "mtime": stat.st_mtime
    }


def extract_audio_features(path: Path) -> AudioFeatures:
    meta = extract_metadata(path)

    features = AudioFeatures(
        path=str(path),
        size=meta["size"],
        mtime=meta["mtime"]
    )

    # -------------------------
    # LEVEL 2 (librosa)
    # -------------------------
    if HAS_LIBROSA:
        try:
            y, sr = librosa.load(path, sr=None, mono=True)

            features.duration = librosa.get_duration(y=y, sr=sr)

            chroma = librosa.feature.chroma_stft(y=y, sr=sr).mean(axis=1)
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13).mean(axis=1)

            features.chroma = chroma.astype(np.float32)
            features.mfcc = mfcc.astype(np.float32)

        except Exception:
            pass

    # -------------------------
    # LEVEL 3 (OpenL3 embedding)
    # -------------------------
    if HAS_OPENL3:
        try:
            audio, sr = sf.read(path)
            emb, _ = openl3.get_audio_embedding(
                audio,
                sr,
                content_type="music"
            )
            features.embedding = emb.mean(axis=0).astype(np.float32)
        except Exception:
            pass

    return features


# =========================================================
# SIMILARITY ENGINE
# =========================================================

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(
        np.dot(a, b) /
        (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)
    )


def level1_similarity(a: AudioFeatures, b: AudioFeatures) -> float:
    size_diff = abs(a.size - b.size) / max(a.size, b.size, 1)

    if not a.duration or not b.duration:
        duration_diff = 1.0
    else:
        duration_diff = abs(a.duration - b.duration) / max(a.duration, b.duration, 1)

    return 1 - (0.6 * size_diff + 0.4 * duration_diff)


def level2_similarity(a: AudioFeatures, b: AudioFeatures) -> float:
    if a.chroma is None or b.chroma is None:
        return 0.0

    chroma_sim = cosine(a.chroma, b.chroma)

    if a.mfcc is None or b.mfcc is None:
        return chroma_sim

    mfcc_sim = cosine(a.mfcc, b.mfcc)

    return 0.5 * chroma_sim + 0.5 * mfcc_sim


def level3_similarity(a: AudioFeatures, b: AudioFeatures) -> float:
    if a.embedding is None or b.embedding is None:
        return 0.0

    return cosine(a.embedding, b.embedding)


def similarity(a: AudioFeatures, b: AudioFeatures) -> float:
    """
    Full tiered similarity engine
    """

    l1 = level1_similarity(a, b)

    # fast reject
    if l1 < 0.85:
        return 0.0

    l2 = level2_similarity(a, b)

    # partial similarity only
    if l2 < 0.75:
        return 0.7 * l1 + 0.3 * l2

    l3 = level3_similarity(a, b)

    return 0.4 * l1 + 0.2 * l2 + 0.4 * l3


# =========================================================
# PUBLIC API
# =========================================================

class AudioSimilarityEngine:
    def __init__(self, db_path: str = ".audio_index.db"):
        self.db = AudioIndex(Path(db_path))

    def load(self, path: str) -> AudioFeatures:
        p = Path(path)

        cached = self.db.get(str(p))

        current = extract_audio_features(p)

        # cache hit → reuse stored features if unchanged
        if cached and cached[2] == current.mtime:
            current.chroma = _unpack(cached[5])
            current.mfcc = _unpack(cached[6])
            current.embedding = _unpack(cached[7])
            current.duration = cached[3]

            return current

        # cache miss → compute & store
        self.db.upsert(current)

        return current

    def get_duration_candidates(self, target_duration: float, tolerance: float = 10):
        cur = self.db.cur  # or self.db.conn.cursor()

        cur.execute("""
            SELECT path, duration
            FROM file_index
            WHERE duration IS NOT NULL
            AND abs(duration - ?) < ?
        """, (target_duration, tolerance))

        return cur.fetchall()

    def compare(self, file_a: str, file_b: str) -> float:
        a = self.load(file_a)
        b = self.load(file_b)

        return similarity(a, b)

    def find_similar(self, target: str, candidates: list[str], threshold: float = 0.85):
        results = []

        a = self.load(target)

        for c in candidates:
            b = self.load(c)
            score = similarity(a, b)

            if score >= threshold:
                results.append((c, score))

        return sorted(results, key=lambda x: x[1], reverse=True)
    
    
    def find_similar_indexed(self, target: str, threshold: float = 0.85):
        candidates = self.db.get_all_audio_files()

        results = []

        a = self.load(target)

        for c in candidates:
            if c == target:
                continue

            b = self.load(c)
            score = similarity(a, b)

            if score >= threshold:
                results.append((c, score))

        return sorted(results, key=lambda x: x[1], reverse=True)
    
