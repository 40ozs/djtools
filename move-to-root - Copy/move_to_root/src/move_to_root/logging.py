import json
from datetime import datetime

def log(args, level, message, mode="apply"):
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": level,
        "mode": mode,
        "message": message,
        "path": getattr(args, "path", None),
        "dry_run": mode == "scan"
    }

    with open("move.log", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")