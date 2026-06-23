#!/usr/bin/env python3
"""Discover GitHub skill candidates without ingesting them into the trusted registry."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SEARCH_QUERIES = [
    "filename:skill.yaml ai agent skill",
    "filename:SKILL.md ai agent skill",
    "path:skills filename:skill.yaml",
    "path:skills filename:SKILL.md",
]


@dataclass
class CandidateDraft:
    repo: str
    repo_url: str
    source_path: str
    default_branch: str
    stars: int
    updated_at: str
    license: str
    topics: list[str]
    html_urls: list[str] = field(default_factory=list)
    detected_files: set[str] = field(default_factory=set)


def normalized_git_url(repo: str) -> str:
    return f"https://github.com/{repo}.git"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def candidate_source_path(file_path: str) -> str:
    if file_path in {"SKILL.md", "skill.yaml"}:
        return "."
    parent = str(Path(file_path).parent).replace("\\", "/")
    return "." if parent == "." else parent


def detected_file_name(file_path: str) -> str:
    return Path(file_path).name


def candidate_name(source_path: str, repo: str) -> str:
    if source_path == ".":
        return repo.split("/", 1)[1].lower().replace("_", "-")
    return Path(source_path).name.lower().replace("_", "-")


def license_spdx(repository: dict[str, Any]) -> str:
    license_info = repository.get("license")
    if isinstance(license_info, dict):
        spdx = license_info.get("spdx_id")
        if isinstance(spdx, str) and spdx.strip():
            return spdx
    return "NOASSERTION"


def repository_topics(repository: dict[str, Any]) -> list[str]:
    topics = repository.get("topics")
    if isinstance(topics, list):
        return sorted(str(topic) for topic in topics if isinstance(topic, str) and topic.strip())
    return []


def read_registry_sources(root: Path) -> set[tuple[str, str]]:
    index_path = root / "skillhub.index.json"
    if not index_path.is_file():
        return set()
    index = load_json(index_path)
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


def normalize_git_source_url(url: str) -> str:
    normalized = url.strip()
    if normalized.startswith("git@github.com:"):
        normalized = "https://github.com/" + normalized.removeprefix("git@github.com:")
    if normalized.startswith("http://github.com/"):
        normalized = "https://github.com/" + normalized.removeprefix("http://github.com/")
    if normalized.startswith("https://github.com/") and not normalized.endswith(".git"):
        normalized += ".git"
    return normalized


def parse_code_search_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("items")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def github_api_get(url: str, token: str | None) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed ({exc.code}): {url}\n{detail}") from exc


def fetch_github_code_search(query: str, token: str | None, per_page: int) -> dict[str, Any]:
    params = urllib.parse.urlencode({"q": query, "per_page": per_page})
    return github_api_get(f"https://api.github.com/search/code?{params}", token)


def load_search_payloads(paths: list[str], queries: list[str], token: str | None, per_page: int) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for raw_path in paths:
        payloads.append(load_json(Path(raw_path)))
    for query in queries:
        payloads.append(fetch_github_code_search(query, token, per_page))
    return payloads


def drafts_from_payloads(payloads: list[dict[str, Any]]) -> dict[tuple[str, str], CandidateDraft]:
    drafts: dict[tuple[str, str], CandidateDraft] = {}
    for payload in payloads:
        for item in parse_code_search_items(payload):
            file_path = item.get("path")
            repository = item.get("repository")
            if not isinstance(file_path, str) or not isinstance(repository, dict):
                continue
            basename = detected_file_name(file_path)
            if basename not in {"SKILL.md", "skill.yaml"}:
                continue
            repo = repository.get("full_name")
            if not isinstance(repo, str) or "/" not in repo:
                continue
            source_path = candidate_source_path(file_path)
            key = (repo, source_path)
            draft = drafts.get(key)
            if draft is None:
                repo_html_url = repository.get("html_url")
                repo_default_branch = repository.get("default_branch")
                repo_stars = repository.get("stargazers_count")
                repo_updated_at = repository.get("updated_at")
                draft = CandidateDraft(
                    repo=repo,
                    repo_url=repo_html_url if isinstance(repo_html_url, str) else f"https://github.com/{repo}",
                    source_path=source_path,
                    default_branch=repo_default_branch if isinstance(repo_default_branch, str) else "main",
                    stars=repo_stars if isinstance(repo_stars, int) else 0,
                    updated_at=repo_updated_at if isinstance(repo_updated_at, str) else "",
                    license=license_spdx(repository),
                    topics=repository_topics(repository),
                )
                drafts[key] = draft
            html_url = item.get("html_url")
            if isinstance(html_url, str) and html_url not in draft.html_urls:
                draft.html_urls.append(html_url)
            draft.detected_files.add(basename)
    return drafts


def build_candidate(draft: CandidateDraft, discovered_at: str) -> dict[str, Any]:
    detected_files = sorted(draft.detected_files)
    detected_format = "skillhub-package" if {"SKILL.md", "skill.yaml"}.issubset(draft.detected_files) else "skill-entrypoint"
    return {
        "id": f"github:{draft.repo}:{draft.source_path}",
        "source_provider": "github",
        "repo": draft.repo,
        "repo_url": draft.repo_url,
        "default_branch": draft.default_branch,
        "source": {
            "type": "git",
            "url": normalized_git_url(draft.repo),
            "path": draft.source_path,
        },
        "namespace": "discovered",
        "name": candidate_name(draft.source_path, draft.repo),
        "detected_format": detected_format,
        "detected_files": detected_files,
        "urls": sorted(draft.html_urls),
        "license": draft.license,
        "stars": draft.stars,
        "repo_updated_at": draft.updated_at,
        "topics": draft.topics,
        "trust_level": "discovered",
        "scan_status": "pending",
        "discovered_at": discovered_at,
    }


def discover_candidates(root: Path, payloads: list[dict[str, Any]], discovered_at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    existing_sources = read_registry_sources(root)
    candidates: list[dict[str, Any]] = []
    skipped_existing: list[dict[str, Any]] = []
    for key, draft in sorted(drafts_from_payloads(payloads).items()):
        source_key = (normalized_git_url(draft.repo), draft.source_path)
        if source_key in existing_sources:
            skipped_existing.append({"repo": draft.repo, "source_path": draft.source_path, "reason": "already indexed"})
            continue
        candidates.append(build_candidate(draft, discovered_at))
    return candidates, skipped_existing


def build_pool(candidates: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "generated_at": generated_at,
        "description": "Discovered skill candidates. Human review is required before registry ingest.",
        "candidates": candidates,
    }


def build_report(candidates: list[dict[str, Any]], skipped_existing: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "candidate_count": len(candidates),
        "skipped_existing_count": len(skipped_existing),
        "candidates": [
            {
                "id": candidate["id"],
                "repo": candidate["repo"],
                "source_path": candidate["source"]["path"],
                "detected_format": candidate["detected_format"],
                "license": candidate["license"],
                "stars": candidate["stars"],
            }
            for candidate in candidates
        ],
        "skipped_existing": skipped_existing,
    }


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def run_gh_code_search(query: str, limit: int) -> dict[str, Any]:
    command = ["gh", "search", "code", query, "--json", "path,repository,url", "--limit", str(limit)]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr + result.stdout)
    rows = json.loads(result.stdout)
    items: list[dict[str, Any]] = []
    for row in rows:
        repo = row.get("repository") if isinstance(row, dict) else None
        if not isinstance(repo, dict):
            continue
        full_name = repo.get("nameWithOwner") or repo.get("fullName") or repo.get("full_name")
        if not isinstance(full_name, str):
            continue
        items.append(
            {
                "path": row.get("path"),
                "html_url": row.get("url"),
                "repository": {
                    "full_name": full_name,
                    "html_url": f"https://github.com/{full_name}",
                    "stargazers_count": repo.get("stargazerCount", 0),
                    "updated_at": repo.get("updatedAt", ""),
                    "license": {"spdx_id": repo.get("licenseInfo", {}).get("spdxId", "NOASSERTION")} if isinstance(repo.get("licenseInfo"), dict) else None,
                    "topics": [],
                    "default_branch": repo.get("defaultBranchRef", {}).get("name", "main") if isinstance(repo.get("defaultBranchRef"), dict) else "main",
                },
            }
        )
    return {"total_count": len(items), "items": items}


def main(argv: list[str] | None = None) -> int:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    parser = argparse.ArgumentParser(description="Discover GitHub skill candidates without ingesting them into skillhub.index.json.")
    parser.add_argument("--root", default=".", help="Registry repository root.")
    parser.add_argument("--output", default="candidates/discovered.json", help="Candidate pool JSON path.")
    parser.add_argument("--report-json", default="candidate-discovery-report.json", help="Discovery report JSON path.")
    parser.add_argument("--discovered-at", default=now, help="Timestamp for generated_at/discovered_at fields.")
    parser.add_argument("--github-code-search-json", action="append", default=[], help="Read a GitHub code search API JSON fixture/result. Can be repeated.")
    parser.add_argument("--github-query", action="append", default=[], help="Run a GitHub code search API query. Can be repeated.")
    parser.add_argument("--use-default-github-queries", action="store_true", help="Run the built-in GitHub code search query set.")
    parser.add_argument("--github-token", default=os.environ.get("GITHUB_TOKEN"), help="GitHub token for search API. Defaults to GITHUB_TOKEN.")
    parser.add_argument("--per-page", type=int, default=50, help="GitHub API results per query.")
    parser.add_argument("--check", action="store_true", help="Fail if the candidate pool on disk differs from newly discovered candidates.")
    args = parser.parse_args(argv)

    root = Path(args.root)
    queries = list(args.github_query)
    if args.use_default_github_queries:
        queries.extend(DEFAULT_SEARCH_QUERIES)
    if not args.github_code_search_json and not queries:
        print("discover candidates failed: provide --github-code-search-json, --github-query, or --use-default-github-queries", file=sys.stderr)
        return 2

    try:
        payloads = load_search_payloads(args.github_code_search_json, queries, args.github_token, args.per_page)
        candidates, skipped_existing = discover_candidates(root, payloads, args.discovered_at)
        pool = build_pool(candidates, args.discovered_at)
        report = build_report(candidates, skipped_existing)
    except Exception as exc:
        print(f"discover candidates failed: {exc}", file=sys.stderr)
        return 2

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = root / output_path
    report_path = Path(args.report_json)
    if not report_path.is_absolute():
        report_path = root / report_path

    if args.check:
        existing = output_path.read_text(encoding="utf-8") if output_path.is_file() else ""
        rendered = canonical_json(pool)
        if existing != rendered:
            print("candidate pool is out of date", file=sys.stderr)
            return 1
        print("candidate pool already current")
        return 0

    write_json(output_path, pool)
    write_json(report_path, report)
    print(f"discovered {len(candidates)} candidates, skipped {len(skipped_existing)} already indexed sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
