#!/usr/bin/env python3
"""Ingest a reviewed discovered candidate into skillhub.index.json as a low-trust git entry."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWED_TARGETS = {"codex", "claude", "gemini"}
DEFAULT_CANDIDATES_PATH = "candidates/discovered.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def normalize_git_source_url(url: str) -> str:
    normalized = url.strip()
    if normalized.startswith("git@github.com:"):
        normalized = "https://github.com/" + normalized.removeprefix("git@github.com:")
    if normalized.startswith("http://github.com/"):
        normalized = "https://github.com/" + normalized.removeprefix("http://github.com/")
    if normalized.startswith("https://github.com/") and not normalized.endswith(".git"):
        normalized += ".git"
    return normalized


def candidate_pool_path(root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else root / path


def index_path(root: Path) -> Path:
    return root / "skillhub.index.json"


def find_candidate(pool: dict[str, Any], candidate_id: str) -> dict[str, Any]:
    candidates = pool.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("candidate pool candidates must be an array")
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("id") == candidate_id:
            return candidate
    raise ValueError(f"candidate not found: {candidate_id}")


def remove_candidate(pool: dict[str, Any], candidate_id: str) -> dict[str, Any]:
    updated = dict(pool)
    candidates = pool.get("candidates", [])
    updated["candidates"] = [candidate for candidate in candidates if not (isinstance(candidate, dict) and candidate.get("id") == candidate_id)]
    return updated


def validate_identity_part(value: str, field: str) -> str:
    if not value or "/" in value or "\\" in value or value in {".", ".."}:
        raise ValueError(f"{field} must be a non-empty identity segment")
    return value


def existing_sources(index: dict[str, Any]) -> set[tuple[str, str]]:
    sources: set[tuple[str, str]] = set()
    for entry in index.get("skills", []):
        if not isinstance(entry, dict):
            continue
        source = entry.get("source")
        if not isinstance(source, dict) or source.get("type") != "git":
            continue
        url = source.get("url")
        path = source.get("path")
        if isinstance(url, str) and isinstance(path, str):
            sources.add((normalize_git_source_url(url), path or "."))
    return sources


def existing_identities(index: dict[str, Any]) -> set[str]:
    return {entry["identity"] for entry in index.get("skills", []) if isinstance(entry, dict) and isinstance(entry.get("identity"), str)}


def build_entry(candidate: dict[str, Any], namespace: str, version: str, description: str, targets: list[str], maintainers: list[str], updated_at: str) -> dict[str, Any]:
    name = validate_identity_part(str(candidate.get("name") or ""), "candidate.name")
    namespace = validate_identity_part(namespace, "namespace")
    unsupported_targets = sorted(set(targets) - ALLOWED_TARGETS)
    if unsupported_targets:
        raise ValueError(f"unsupported targets: {', '.join(unsupported_targets)}")
    if not targets:
        raise ValueError("targets must not be empty")
    if not maintainers:
        raise ValueError("at least one maintainer is required")
    source = candidate.get("source")
    if not isinstance(source, dict) or source.get("type") != "git":
        raise ValueError("candidate source must be a git source")
    source_url = source.get("url")
    source_path = source.get("path")
    if not isinstance(source_url, str) or not isinstance(source_path, str):
        raise ValueError("candidate source.url and source.path must be strings")
    raw_topics = candidate.get("topics")
    topics = raw_topics if isinstance(raw_topics, list) else []
    tags = [str(topic) for topic in topics if isinstance(topic, str) and topic.strip()]
    if not tags:
        tags = ["community"]
    license_value = candidate.get("license") if isinstance(candidate.get("license"), str) else "NOASSERTION"
    return {
        "identity": f"{namespace}/{name}",
        "name": name,
        "namespace": namespace,
        "version": version,
        "description": description,
        "targets": targets,
        "tags": tags,
        "source": {
            "type": "git",
            "url": normalize_git_source_url(source_url),
            "path": source_path or ".",
        },
        "maintainers": maintainers,
        "license": license_value,
        "trust": {"level": "community"},
        "featured": False,
        "updated_at": updated_at,
    }


def ingest_candidate(root: Path, candidate_path: Path, candidate_id: str, namespace: str, version: str, description: str, targets: list[str], maintainers: list[str], updated_at: str, generated_at: str) -> str:
    index = load_json(index_path(root))
    pool = load_json(candidate_path)
    candidate = find_candidate(pool, candidate_id)
    entry = build_entry(candidate, namespace, version, description, targets, maintainers, updated_at)
    source_key = (entry["source"]["url"], entry["source"]["path"])
    if source_key in existing_sources(index):
        raise ValueError(f"source already exists: {entry['source']['url']} {entry['source']['path']}")
    if entry["identity"] in existing_identities(index):
        raise ValueError(f"identity already exists: {entry['identity']}")
    skills = index.get("skills")
    if not isinstance(skills, list):
        raise ValueError("index skills must be an array")
    skills.append(entry)
    skills.sort(key=lambda item: item.get("identity", "") if isinstance(item, dict) else "")
    index["generated_at"] = generated_at
    write_json(index_path(root), index)
    write_json(candidate_path, remove_candidate(pool, candidate_id))
    return str(entry["identity"])


def main(argv: list[str] | None = None) -> int:
    now = datetime.now(timezone.utc)
    parser = argparse.ArgumentParser(description="Ingest one discovered candidate into skillhub.index.json as a low-trust git entry.")
    parser.add_argument("--root", default=".", help="Registry repository root.")
    parser.add_argument("--candidates", default=DEFAULT_CANDIDATES_PATH, help="Candidate pool path.")
    parser.add_argument("--candidate-id", required=True, help="Candidate id to ingest.")
    parser.add_argument("--namespace", default="community", help="Registry namespace for the ingested entry.")
    parser.add_argument("--version", required=True, help="Initial catalog version.")
    parser.add_argument("--description", required=True, help="Reviewed catalog description.")
    parser.add_argument("--targets", required=True, help="Comma-separated targets, e.g. codex,claude.")
    parser.add_argument("--maintainer", action="append", default=[], help="Maintainer name. Can be repeated.")
    parser.add_argument("--updated-at", default=now.date().isoformat(), help="updated_at value for the new entry.")
    parser.add_argument("--generated-at", default=now.isoformat().replace("+00:00", "Z"), help="generated_at value for the index.")
    args = parser.parse_args(argv)

    root = Path(args.root)
    try:
        identity = ingest_candidate(
            root=root,
            candidate_path=candidate_pool_path(root, args.candidates),
            candidate_id=args.candidate_id,
            namespace=args.namespace,
            version=args.version,
            description=args.description,
            targets=split_csv(args.targets),
            maintainers=args.maintainer,
            updated_at=args.updated_at,
            generated_at=args.generated_at,
        )
    except Exception as exc:
        print(f"ingest candidate failed: {exc}", file=sys.stderr)
        return 1
    print(f"ingested {args.candidate_id} as {identity}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
