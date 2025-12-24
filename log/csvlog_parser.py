import argparse
import re
import json
from pathlib import Path

def parse_log(path, min_ms):
    duration_re = re.compile(r"duration:\s*([0-9]+(?:\.[0-9]+)?)\s*ms", re.IGNORECASE)
    deadlock_re = re.compile(r"deadlock detected", re.IGNORECASE)
    error_re = re.compile(r"\bERROR\b", re.IGNORECASE)
    slow = []
    errors = 0
    deadlocks = 0
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = duration_re.search(line)
                if m:
                    ms = float(m.group(1))
                    if ms >= min_ms:
                        slow.append({"duration_ms": ms, "line": line.strip()[:1000]})
                if error_re.search(line):
                    errors += 1
                if deadlock_re.search(line):
                    deadlocks += 1
    except Exception as e:
        return {"error": str(e)}
    slow.sort(key=lambda x: x["duration_ms"], reverse=True)
    return {
        "file": str(path),
        "min_duration_ms": min_ms,
        "slow_count": len(slow),
        "slow_top": slow[:50],
        "errors": errors,
        "deadlocks": deadlocks,
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--path", required=True)
    p.add_argument("--min-duration-ms", type=int, default=1000)
    args = p.parse_args()
    result = parse_log(Path(args.path), args.min_duration_ms)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

