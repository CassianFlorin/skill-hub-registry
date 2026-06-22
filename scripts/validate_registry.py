#!/usr/bin/env python3
"""Validate a skill-hub registry repository."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import PurePosixPath
from pathlib import Path
from typing import Any


ALLOWED_TARGETS = {"codex", "claude", "gemini"}
ALLOWED_TRUST_LEVELS = {"official", "curated", "community", "private", "unknown"}


def parse_simple_yaml(path: Path) -> dict[str, Any]:
    """Parse the small YAML subset used by skill.yaml without extra deps."""
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


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_non_empty_string_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) > 0
        and all(is_non_empty_string(item) for item in value)
    )


def add_error(errors: list[str], scope: str, message: str) -> None:
    errors.append(f"{scope}: {message}")


def validate_required_fields(entry: dict[str, Any], scope: str, errors: list[str]) -> None:
    for field in ("identity", "name", "namespace", "version", "description", "license", "updated_at"):
        if not is_non_empty_string(entry.get(field)):
            add_error(errors, scope, f"{field} must be a non-empty string")

    for field in ("targets", "tags", "maintainers"):
        if not is_non_empty_string_list(entry.get(field)):
            add_error(errors, scope, f"{field} must be a non-empty string list")

    if not isinstance(entry.get("source"), dict):
        add_error(errors, scope, "source must be an object")

    if not isinstance(entry.get("trust"), dict):
        add_error(errors, scope, "trust must be an object")


def validate_identity(entry: dict[str, Any], scope: str, errors: list[str]) -> None:
    identity = entry.get("identity")
    namespace = entry.get("namespace")
    name = entry.get("name")
    if all(is_non_empty_string(value) for value in (identity, namespace, name)):
        expected = f"{namespace}/{name}"
        if identity != expected:
            add_error(errors, scope, f"identity must equal namespace/name: {expected}")


def validate_targets(entry: dict[str, Any], scope: str, errors: list[str]) -> None:
    targets = entry.get("targets")
    if not isinstance(targets, list):
        return
    for target in targets:
        if target not in ALLOWED_TARGETS:
            add_error(errors, scope, f"unsupported target: {target}")


def validate_trust(entry: dict[str, Any], scope: str, errors: list[str]) -> None:
    trust = entry.get("trust")
    if not isinstance(trust, dict):
        return

    level = trust.get("level")
    if level not in ALLOWED_TRUST_LEVELS:
        add_error(errors, scope, f"unsupported trust.level: {level}")

    requires_review = entry.get("featured") is True or level == "official"
    if requires_review and not is_non_empty_string(trust.get("reviewer")):
        add_error(errors, scope, "featured skills require trust.reviewer")
    if requires_review and not is_non_empty_string(trust.get("reviewed_at")):
        add_error(errors, scope, "featured skills require trust.reviewed_at")


def validate_relative_source_path(source_path: str) -> str | None:
    if source_path.startswith("/"):
        return "source.path must be relative"
    if "\\" in source_path:
        return "source.path must use slash separators"
    path = PurePosixPath(source_path)
    if any(part in ("", ".", "..") for part in path.parts):
        return "source.path escapes registry root"
    return None


def validate_source(root: Path, entry: dict[str, Any], scope: str, errors: list[str]) -> Path | None:
    source = entry.get("source")
    if not isinstance(source, dict):
        return None

    source_type = source.get("type")
    source_path = source.get("path")
    if not is_non_empty_string(source_path):
        add_error(errors, scope, "source.path must be a non-empty string")
        return None

    path_error = validate_relative_source_path(source_path)
    if path_error:
        add_error(errors, scope, path_error)
        return None

    if source_type == "git":
        source_url = source.get("url")
        if not is_non_empty_string(source_url) or not source_url.startswith("https://"):
            add_error(errors, scope, "git source.url must be a public https URL")
        source_ref = source.get("ref")
        if source_ref is not None and not is_non_empty_string(source_ref):
            add_error(errors, scope, "git source.ref must be a non-empty string when set")
        sync_metadata = source.get("sync_metadata")
        if sync_metadata is not None and not isinstance(sync_metadata, bool):
            add_error(errors, scope, "git source.sync_metadata must be a boolean when set")
        return None

    if source_type != "registry":
        add_error(errors, scope, f"unsupported source.type: {source_type}")
        return None

    root_resolved = root.resolve()
    resolved = (root / source_path).resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError:
        add_error(errors, scope, "source.path escapes registry root")
        return None

    if not resolved.is_dir():
        add_error(errors, scope, f"source.path directory does not exist: {source_path}")
        return None

    return resolved


def validate_skill_package(skill_dir: Path, entry: dict[str, Any], scope: str, errors: list[str]) -> None:
    skill_md = skill_dir / "SKILL.md"
    skill_yaml = skill_dir / "skill.yaml"

    if not skill_md.is_file():
        add_error(errors, scope, "missing SKILL.md")
    if not skill_yaml.is_file():
        add_error(errors, scope, "missing skill.yaml")
        return

    metadata = parse_simple_yaml(skill_yaml)
    for field in ("name", "namespace", "version", "description"):
        if metadata.get(field) != entry.get(field):
            add_error(
                errors,
                scope,
                f"skill.yaml {field} must match index {field}: {entry.get(field)}",
            )

    yaml_targets = metadata.get("targets")
    if yaml_targets != entry.get("targets"):
        add_error(errors, scope, "skill.yaml targets must match index targets")

    entry_file = metadata.get("entry")
    if entry_file and not (skill_dir / entry_file).is_file():
        add_error(errors, scope, f"skill.yaml entry file does not exist: {entry_file}")


def validate_registry(root: Path) -> list[str]:
    errors: list[str] = []
    index_path = root / "skillhub.index.json"
    if not index_path.is_file():
        return [f"{index_path}: missing skillhub.index.json"]

    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{index_path}: invalid JSON: {exc}"]

    if index.get("schema_version") != "2":
        add_error(errors, "index", "schema_version must be 2")

    skills = index.get("skills")
    if not isinstance(skills, list) or not skills:
        add_error(errors, "index", "skills must be a non-empty array")
        return errors

    seen_identities: set[str] = set()
    seen_namespaced_names: set[str] = set()
    for index_number, entry in enumerate(skills, start=1):
        if not isinstance(entry, dict):
            add_error(errors, f"skill[{index_number}]", "entry must be an object")
            continue

        scope = entry.get("identity") if is_non_empty_string(entry.get("identity")) else f"skill[{index_number}]"
        identity = entry.get("identity")
        if is_non_empty_string(identity):
            if identity in seen_identities:
                add_error(errors, scope, f"duplicate identity: {identity}")
            seen_identities.add(identity)

        namespace = entry.get("namespace")
        name = entry.get("name")
        if is_non_empty_string(namespace) and is_non_empty_string(name):
            namespaced_name = f"{namespace}/{name}"
            if namespaced_name in seen_namespaced_names:
                add_error(errors, scope, f"duplicate namespace/name: {namespaced_name}")
            seen_namespaced_names.add(namespaced_name)

        validate_required_fields(entry, scope, errors)
        validate_identity(entry, scope, errors)
        validate_targets(entry, scope, errors)
        validate_trust(entry, scope, errors)
        skill_dir = validate_source(root, entry, scope, errors)
        if skill_dir is not None:
            validate_skill_package(skill_dir, entry, scope, errors)

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a skill-hub registry repository.")
    parser.add_argument("--root", default=".", help="Registry repository root.")
    args = parser.parse_args(argv)

    root = Path(args.root)
    errors = validate_registry(root)
    if errors:
        print(f"registry validation failed: {len(errors)} errors", file=sys.stderr)
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    skill_count = len(json.loads((root / "skillhub.index.json").read_text(encoding="utf-8"))["skills"])
    print(f"registry validation passed: {skill_count} skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
