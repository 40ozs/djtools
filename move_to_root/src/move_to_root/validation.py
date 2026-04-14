from pathlib import Path

class ValidationError(Exception):
    pass


def validate_args(args):
    root = Path(args.path).resolve()

    if not root.exists():
        raise ValidationError(f"Path does not exist: {root}")

    if not root.is_dir():
        raise ValidationError(f"Path is not a directory: {root}")

    # 🔥 COMMAND-SPECIFIC VALIDATION
    if args.command == "apply":
        if getattr(args, "workers", 1) <= 0:
            raise ValidationError("workers must be > 0")

        if getattr(args, "retry_count", 0) < 0:
            raise ValidationError("retry-count must be >= 0")

        if getattr(args, "retry_delay", 0) < 0:
            raise ValidationError("retry-delay must be >= 0")

    return True