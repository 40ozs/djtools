from pathlib import Path
from ..audio_similarity import AudioSimilarityEngine


def find_similar_cli(args):
    engine = AudioSimilarityEngine()

    print(f"\nTarget: {args.target}")
    print("Using SQLite index (fast mode)\n")

    results = engine.find_similar_indexed(
        args.target,
        threshold=args.threshold
    )

    if not results:
        print("No similar files found.")
        return

    print("\nSIMILAR FILES")
    print("-" * 40)

    for path, score in results[: args.top if hasattr(args, "top") else None]:
        print(f"{score:.3f} → {path}")