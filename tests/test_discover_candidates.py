from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import scripts.discover_candidates as discover_candidates


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "discover_candidates.py"


def write_index(root: Path, skills: list[dict]) -> None:
    (root / "skillhub.index.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "registry": "hub",
                "generated_at": "2026-06-23T00:00:00Z",
                "skills": skills,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def git_entry(identity: str, repo: str, source_path: str) -> dict:
    namespace, name = identity.split("/", 1)
    return {
        "identity": identity,
        "name": name,
        "namespace": namespace,
        "version": "0.1.0",
        "description": "Already indexed skill.",
        "targets": ["codex"],
        "tags": ["test"],
        "source": {
            "type": "git",
            "url": f"https://github.com/{repo}.git",
            "path": source_path,
        },
        "maintainers": ["Example"],
        "license": "MIT",
        "trust": {"level": "community"},
        "featured": False,
        "updated_at": "2026-06-23",
    }


def write_search_fixture(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "total_count": 4,
                "items": [
                    {
                        "name": "skill.yaml",
                        "path": "skills/python-review/skill.yaml",
                        "html_url": "https://github.com/acme/agent-skills/blob/main/skills/python-review/skill.yaml",
                        "repository": {
                            "full_name": "acme/agent-skills",
                            "html_url": "https://github.com/acme/agent-skills",
                            "stargazers_count": 42,
                            "updated_at": "2026-06-20T12:00:00Z",
                            "license": {"spdx_id": "MIT"},
                            "topics": ["ai-agent", "skills"],
                            "default_branch": "main",
                        },
                    },
                    {
                        "name": "SKILL.md",
                        "path": "skills/python-review/SKILL.md",
                        "html_url": "https://github.com/acme/agent-skills/blob/main/skills/python-review/SKILL.md",
                        "repository": {
                            "full_name": "acme/agent-skills",
                            "html_url": "https://github.com/acme/agent-skills",
                            "stargazers_count": 42,
                            "updated_at": "2026-06-20T12:00:00Z",
                            "license": {"spdx_id": "MIT"},
                            "topics": ["ai-agent", "skills"],
                            "default_branch": "main",
                        },
                    },
                    {
                        "name": "skill.yaml",
                        "path": "skills/already-indexed/skill.yaml",
                        "html_url": "https://github.com/acme/agent-skills/blob/main/skills/already-indexed/skill.yaml",
                        "repository": {
                            "full_name": "acme/agent-skills",
                            "html_url": "https://github.com/acme/agent-skills",
                            "stargazers_count": 42,
                            "updated_at": "2026-06-20T12:00:00Z",
                            "license": {"spdx_id": "MIT"},
                            "topics": ["ai-agent", "skills"],
                            "default_branch": "main",
                        },
                    },
                    {
                        "name": "SKILL.md",
                        "path": "SKILL.md",
                        "html_url": "https://github.com/solo/root-skill/blob/main/SKILL.md",
                        "repository": {
                            "full_name": "solo/root-skill",
                            "html_url": "https://github.com/solo/root-skill",
                            "stargazers_count": 7,
                            "updated_at": "2026-06-21T12:00:00Z",
                            "license": None,
                            "topics": [],
                            "default_branch": "main",
                        },
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def run_discovery(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class DiscoverCandidatesTest(unittest.TestCase):
    def test_discovery_writes_deduped_candidate_pool_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "github-code-search.json"
            output = root / "candidates" / "discovered.json"
            report = root / "candidate-discovery-report.json"
            write_index(root, [git_entry("community/already-indexed", "acme/agent-skills", "skills/already-indexed")])
            write_search_fixture(fixture)

            result = run_discovery(
                root,
                "--github-code-search-json",
                str(fixture),
                "--output",
                str(output),
                "--report-json",
                str(report),
                "--discovered-at",
                "2026-06-23T00:00:00Z",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            pool = json.loads(output.read_text(encoding="utf-8"))
            summary = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(pool["schema_version"], "1")
            self.assertEqual(pool["generated_at"], "2026-06-23T00:00:00Z")
            self.assertEqual(len(pool["candidates"]), 2)
            self.assertEqual(summary["candidate_count"], 2)
            self.assertEqual(summary["skipped_existing_count"], 1)

            first = pool["candidates"][0]
            self.assertEqual(first["id"], "github:acme/agent-skills:skills/python-review")
            self.assertEqual(first["repo"], "acme/agent-skills")
            self.assertEqual(first["source"], {"type": "git", "url": "https://github.com/acme/agent-skills.git", "path": "skills/python-review"})
            self.assertEqual(first["name"], "python-review")
            self.assertEqual(first["namespace"], "discovered")
            self.assertEqual(first["detected_format"], "skillhub-package")
            self.assertEqual(first["detected_files"], ["SKILL.md", "skill.yaml"])
            self.assertEqual(first["trust_level"], "discovered")
            self.assertEqual(first["scan_status"], "pending")
            self.assertEqual(first["license"], "MIT")
            self.assertEqual(first["stars"], 42)

            root_candidate = pool["candidates"][1]
            self.assertEqual(root_candidate["source"]["path"], ".")
            self.assertEqual(root_candidate["license"], "NOASSERTION")

    def test_check_mode_fails_when_candidate_pool_would_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "github-code-search.json"
            output = root / "candidates" / "discovered.json"
            write_index(root, [])
            write_search_fixture(fixture)

            initial = run_discovery(root, "--github-code-search-json", str(fixture), "--output", str(output), "--discovered-at", "2026-06-23T00:00:00Z")
            check = run_discovery(root, "--github-code-search-json", str(fixture), "--output", str(output), "--check", "--discovered-at", "2026-06-24T00:00:00Z")

            self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)
            self.assertEqual(check.returncode, 1, check.stdout + check.stderr)
            self.assertIn("candidate pool is out of date", check.stderr)
    def test_soft_query_failures_are_reported_without_blocking_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "candidates" / "discovered.json"
            report = root / "candidate-discovery-report.json"
            write_index(root, [])

            with mock.patch.object(
                discover_candidates,
                "fetch_github_code_search",
                side_effect=RuntimeError("GitHub API request failed (429): secondary rate limit"),
            ):
                payloads, query_errors = discover_candidates.load_search_payloads(
                    [],
                    ["path:skills filename:skill.yaml"],
                    None,
                    50,
                )
            candidates, skipped_existing = discover_candidates.discover_candidates(root, payloads, "2026-06-23T00:00:00Z")
            pool = discover_candidates.build_pool(candidates, "2026-06-23T00:00:00Z")
            summary = discover_candidates.build_report(candidates, skipped_existing, query_errors)
            discover_candidates.write_json(output, pool)
            discover_candidates.write_json(report, summary)

            self.assertEqual(payloads, [])
            self.assertEqual(len(query_errors), 1)
            self.assertIn("secondary rate limit", query_errors[0]["error"])
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["candidates"], [])
            saved_report = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(saved_report["candidate_count"], 0)
            self.assertEqual(saved_report["query_error_count"], 1)
            self.assertEqual(saved_report["query_errors"][0]["query"], "path:skills filename:skill.yaml")


if __name__ == "__main__":
    unittest.main()
