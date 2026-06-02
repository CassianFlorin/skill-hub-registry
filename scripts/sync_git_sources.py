#!/usr/bin/env python3
"""Refresh catalog metadata for git-backed skill entries."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_simple_yaml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_list: str | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if current_list and line.startswith("  - "):
            data[current_list].append(line[4:].strip())
            continue

        current_list = None
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            data[key] = value.strip('"').strip("'")
        else:
            data[key] = []
            current_list = key

    return data


def run_git(cwd: Path | None, *args: str) -> None:
    command = ["git", *args]
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        location = str(cwd) if cwd is not None else "."
        raise RuntimeError(f"{location}: git {' '.join(args)} failed\n{result.stderr}{result.stdout}")


def cache_name(source_url: str, source_ref: str | None) -> str:
    suffix = hashlib.sha256(f"{source_url}@{source_ref or ''}".encode("utf-8")).hexdigest()[:16]
    return f"source-{suffix}"


def ensure_git_cache(cache_dir: Path, source_url: str, source_ref: str | None) -> Path:
    cache_path = cache_dir / cache_name(source_url, source_ref)
    if (cache_path / ".git").is_dir():
        if source_ref:
            run_git(cache_path, "fetch", "--tags", "--prune")
        else:
            run_git(cache_path, "pull", "--ff-only")
    else:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        run_git(None, "clone", source_url, str(cache_path))

    if source_ref:
        run_git(cache_path, "checkout", "--detach", source_ref)
    return cache_path


def safe_source_path(cache_path: Path, source_path: str) -> Path:
    if source_path.startswith("/") or "\\" in source_path:
        raise ValueError(f"source.path must be a relative slash path: {source_path}")
    resolved = (cache_path / source_path).resolve()
    try:
        resolved.relative_to(cache_path.resolve())
    except ValueError as exc:
        raise ValueError(f"source.path escapes git source: {source_path}") from exc
    return resolved


def checksum_dir(path: Path) -> str:
    digest = hashlib.sha256()
    for file_path in sorted(item for item in path.rglob("*") if item.is_file()):
        relative = file_path.relative_to(path).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_path.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def require_string(metadata: dict[str, Any], field: str, identity: str) -> str:
    value = metadata.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{identity}: skill.yaml {field} must be a non-empty string")
    return value


def require_string_list(metadata: dict[str, Any], field: str, identity: str) -> list[str]:
    value = metadata.get(field)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{identity}: skill.yaml {field} must be a non-empty string list")
    return value


def synced_entry(entry: dict[str, Any], source_dir: Path, updated_at: str) -> dict[str, Any]:
    identity = entry.get("identity", "<unknown>")
    metadata_path = source_dir / "skill.yaml"
    if not metadata_path.is_file():
        raise ValueError(f"{identity}: missing remote skill.yaml at {source_dir}")

    metadata = parse_simple_yaml(metadata_path)
    name = require_string(metadata, "name", identity)
    namespace = require_string(metadata, "namespace", identity)
    expected_identity = f"{namespace}/{name}"
    if identity != expected_identity:
        raise ValueError(f"{identity}: remote identity is {expected_identity}")

    updated = copy.deepcopy(entry)
    updated["name"] = name
    updated["namespace"] = namespace
    updated["version"] = require_string(metadata, "version", identity)
    updated["description"] = require_string(metadata, "description", identity)
    updated["targets"] = require_string_list(metadata, "targets", identity)
    updated["tags"] = metadata.get("tags") if isinstance(metadata.get("tags"), list) else []
    author = metadata.get("author")
    updated["maintainers"] = [author] if isinstance(author, str) and author.strip() else []
    updated["updated_at"] = updated_at
    updated["checksum"] = checksum_dir(source_dir)
    return updated


def sync_index(root: Path, cache_dir: Path, updated_at: str, generated_at: str) -> tuple[dict[str, Any], list[str]]:
    index_path = root / "skillhub.index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    updated_index = copy.deepcopy(index)
    changed: list[str] = []

    for position, entry in enumerate(index.get("skills", [])):
        source = entry.get("source", {})
        if not isinstance(source, dict) or source.get("type") != "git":
            continue

        source_url = source.get("url")
        source_path = source.get("path")
        source_ref = source.get("ref")
        identity = entry.get("identity", f"skill[{position + 1}]")
        if not isinstance(source_url, str) or not source_url.strip():
            raise ValueError(f"{identity}: git source.url must be a non-empty string")
        if not isinstance(source_path, str) or not source_path.strip():
            raise ValueError(f"{identity}: git source.path must be a non-empty string")
        if source_ref is not None and not isinstance(source_ref, str):
            raise ValueError(f"{identity}: git source.ref must be a string when set")

        cache_path = ensure_git_cache(cache_dir, source_url, source_ref)
        source_dir = safe_source_path(cache_path, source_path)
        new_entry = synced_entry(entry, source_dir, updated_at)
        if new_entry != entry:
            changed.append(str(identity))
            updated_index["skills"][position] = new_entry

    if changed:
        updated_index["generated_at"] = generated_at
    return updated_index, changed


def write_index(root: Path, index: dict[str, Any]) -> None:
    data = json.dumps(index, indent=2) + "\n"
    (root / "skillhub.index.json").write_text(data, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    now = datetime.now(timezone.utc)
    parser = argparse.ArgumentParser(description="Refresh git source metadata in skillhub.index.json.")
    parser.add_argument("--root", default=".", help="Registry repository root.")
    parser.add_argument("--cache-dir", help="Git cache directory. Defaults to <root>/.cache/git-sources.")
    parser.add_argument("--updated-at", default=now.date().isoformat(), help="updated_at value for changed skills.")
    parser.add_argument("--generated-at", default=now.isoformat().replace("+00:00", "Z"), help="generated_at value when changes are found.")
    parser.add_argument("--check", action="store_true", help="Fail if git source metadata is out of sync.")
    args = parser.parse_args(argv)

    root = Path(args.root)
    cache_dir = Path(args.cache_dir) if args.cache_dir else root / ".cache" / "git-sources"
    try:
        updated_index, changed = sync_index(root, cache_dir, args.updated_at, args.generated_at)
    except Exception as exc:
        print(f"sync git sources failed: {exc}", file=sys.stderr)
        return 2

    if args.check:
        for identity in changed:
            print(f"out of sync: {identity}", file=sys.stderr)
        return 1 if changed else 0

    if changed:
        write_index(root, updated_index)
        for identity in changed:
            print(f"updated {identity}")
    else:
        print("git sources already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
