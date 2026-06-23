#!/usr/bin/env python3
"""Promote registry trust levels after explicit human review."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWED_LEVELS = {"official", "curated", "community", "private", "unknown"}
REVIEW_REQUIRED_LEVELS = {"official", "curated"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def promote(root: Path, identity: str, level: str, reviewer: str | None, reviewed_at: str | None, featured: bool | None, generated_at: str) -> None:
    if level not in ALLOWED_LEVELS:
        raise ValueError(f"unsupported trust level: {level}")
    if level in REVIEW_REQUIRED_LEVELS and (not reviewer or not reviewed_at):
        raise ValueError("reviewer and reviewed_at are required for curated or official promotions")

    index_path = root / "skillhub.index.json"
    index = load_json(index_path)
    skills = index.get("skills")
    if not isinstance(skills, list):
        raise ValueError("index skills must be an array")

    for entry in skills:
        if not isinstance(entry, dict) or entry.get("identity") != identity:
            continue
        trust: dict[str, Any] = {"level": level}
        if reviewer and reviewed_at:
            trust["reviewer"] = reviewer
            trust["reviewed_at"] = reviewed_at
        entry["trust"] = trust
        if featured is not None:
            entry["featured"] = featured
        index["generated_at"] = generated_at
        write_json(index_path, index)
        return
    raise ValueError(f"identity not found: {identity}")


def main(argv: list[str] | None = None) -> int:
    now = datetime.now(timezone.utc)
    parser = argparse.ArgumentParser(description="Promote a registry entry trust level after human review.")
    parser.add_argument("--root", default=".", help="Registry repository root.")
    parser.add_argument("--identity", required=True, help="Registry identity, e.g. community/python-review.")
    parser.add_argument("--level", required=True, choices=sorted(ALLOWED_LEVELS), help="Target trust level.")
    parser.add_argument("--reviewer", help="Reviewer name required for curated/official.")
    parser.add_argument("--reviewed-at", help="Review date required for curated/official.")
    parser.add_argument("--featured", action="store_true", help="Mark entry as featured.")
    parser.add_argument("--unfeatured", action="store_true", help="Mark entry as not featured.")
    parser.add_argument("--generated-at", default=now.isoformat().replace("+00:00", "Z"), help="generated_at value for the index.")
    args = parser.parse_args(argv)

    featured: bool | None
    if args.featured and args.unfeatured:
        print("promote trust failed: choose only one of --featured or --unfeatured", file=sys.stderr)
        return 1
    if args.featured:
        featured = True
    elif args.unfeatured:
        featured = False
    else:
        featured = None

    try:
        promote(Path(args.root), args.identity, args.level, args.reviewer, args.reviewed_at, featured, args.generated_at)
    except Exception as exc:
        print(f"promote trust failed: {exc}", file=sys.stderr)
        return 1
    print(f"promoted {args.identity} to {args.level}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
