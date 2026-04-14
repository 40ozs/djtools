import argparse
from pathlib import Path

from .audio_similarity import AudioSimilarityEngine
from .validation import validate_args, ValidationError

from .commands.scan import scan
from .commands.apply import apply
from .commands.rollback import rollback
from .commands.status import status
# from .commands.history import history
from .commands.find_similar import find_similar_cli


def build_parser():
    parser = argparse.ArgumentParser(
        prog="move-to-root",
        description="Stateful filesystem flattening CLI (scan/apply/rollback)"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # -----------------------
    # SCAN (dry-run / preview)
    # -----------------------
    scan_p = sub.add_parser("scan", help="Preview file moves (no changes made)")
    scan_p.add_argument("--path", default=".")
    scan_p.add_argument("--include", nargs="*")
    scan_p.add_argument("--exclude", nargs="*")
    scan_p.add_argument("--summary", action="store_true") 
    scan_p.add_argument("--check-duplicates", action="store_true", help="Enable duplicate detection (slow mode)"
)

    # -----------------------
    # APPLY (execute moves)
    # -----------------------
    apply_p = sub.add_parser("apply", help="Execute file moves and persist state")
    apply_p.add_argument("--path", default=".")
    apply_p.add_argument("--include", nargs="*")
    apply_p.add_argument("--exclude", nargs="*")
    apply_p.add_argument("--parallel", action="store_true")
    apply_p.add_argument("--workers", type=int, default=4)
    apply_p.add_argument("--retry-count", type=int, default=3)
    apply_p.add_argument("--retry-delay", type=int, default=500)

    # -----------------------
    # ROLLBACK (undo apply)
    # -----------------------
    rollback_p = sub.add_parser("rollback", help="Rollback last apply operation")
    rollback_p.add_argument("--path", default=".")

    status_p = sub.add_parser("status", help="Show latest run + DB stats")
    status_p.add_argument("--path", default=".")

    history_p = sub.add_parser("history", help="Show recent execution history")
    history_p.add_argument("--path", default=".")


    sim_p = sub.add_parser("find-similar", help="Find similar audio files")
    sim_p.add_argument("target", help="Target audio file")
    sim_p.add_argument("--path", default=".", help="Search directory")
    sim_p.add_argument("--threshold", type=float, default=0.85)
    sim_p.add_argument("--top", type=int, default=20)


    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    try:
        validate_args(args)
    except ValidationError as e:
        print(f"[ERROR] {e}")
        return 1

    if args.command == "scan":
        scan(args)

    elif args.command == "apply":
        apply(args)

    elif args.command == "rollback":
        rollback(args)

    elif args.command == "status":
        status(args)

    elif args.command == "history":
        history(args)
    
    elif args.command == "find-similar":
        find_similar_cli(args)

    elif getattr(args, "check_duplicates", False):
    
        return 0



if __name__ == "__main__":
    raise SystemExit(main())