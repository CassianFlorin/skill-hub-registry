from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INGEST_SCRIPT = REPO_ROOT / "scripts" / "ingest_candidate.py"
PROMOTE_SCRIPT = REPO_ROOT / "scripts" / "promote_trust.py"


def write_index(root: Path) -> None:
    (root / "skillhub.index.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "registry": "hub",
                "generated_at": "2026-06-22T00:00:00Z",
                "skills": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def write_candidate_pool(root: Path) -> None:
    candidate_dir = root / "candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    (candidate_dir / "discovered.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "generated_at": "2026-06-23T00:00:00Z",
                "description": "Discovered skill candidates.",
                "candidates": [
                    {
                        "id": "github:acme/agent-skills:skills/python-review",
                        "source_provider": "github",
                        "repo": "acme/agent-skills",
                        "repo_url": "https://github.com/acme/agent-skills",
                        "default_branch": "main",
                        "source": {
                            "type": "git",
                            "url": "https://github.com/acme/agent-skills.git",
                            "path": "skills/python-review",
                        },
                        "namespace": "discovered",
                        "name": "python-review",
                        "detected_format": "skillhub-package",
                        "detected_files": ["SKILL.md", "skill.yaml"],
                        "urls": [
                            "https://github.com/acme/agent-skills/blob/main/skills/python-review/SKILL.md",
                            "https://github.com/acme/agent-skills/blob/main/skills/python-review/skill.yaml",
                        ],
                        "license": "MIT",
                        "stars": 42,
                        "repo_updated_at": "2026-06-20T12:00:00Z",
                        "topics": ["ai-agent", "review"],
                        "trust_level": "discovered",
                        "scan_status": "pending",
                        "discovered_at": "2026-06-23T00:00:00Z",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def run_script(script: Path, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), "--root", str(root), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class RegistryIngestTest(unittest.TestCase):
    def test_ingest_candidate_appends_low_trust_git_entry_and_removes_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_index(root)
            write_candidate_pool(root)

            result = run_script(
                INGEST_SCRIPT,
                root,
                "--candidate-id",
                "github:acme/agent-skills:skills/python-review",
                "--namespace",
                "community",
                "--version",
                "0.1.0",
                "--description",
                "Reviews Python code for maintainability.",
                "--targets",
                "codex,claude",
                "--maintainer",
                "acme",
                "--updated-at",
                "2026-06-23",
                "--generated-at",
                "2026-06-23T00:00:00Z",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            index = json.loads((root / "skillhub.index.json").read_text(encoding="utf-8"))
            self.assertEqual(index["generated_at"], "2026-06-23T00:00:00Z")
            self.assertEqual(len(index["skills"]), 1)
            entry = index["skills"][0]
            self.assertEqual(entry["identity"], "community/python-review")
            self.assertEqual(entry["name"], "python-review")
            self.assertEqual(entry["namespace"], "community")
            self.assertEqual(entry["version"], "0.1.0")
            self.assertEqual(entry["description"], "Reviews Python code for maintainability.")
            self.assertEqual(entry["targets"], ["codex", "claude"])
            self.assertEqual(entry["tags"], ["ai-agent", "review"])
            self.assertEqual(entry["source"], {"type": "git", "url": "https://github.com/acme/agent-skills.git", "path": "skills/python-review"})
            self.assertEqual(entry["maintainers"], ["acme"])
            self.assertEqual(entry["license"], "MIT")
            self.assertEqual(entry["trust"], {"level": "community"})
            self.assertFalse(entry["featured"])
            self.assertEqual(entry["updated_at"], "2026-06-23")
            pool = json.loads((root / "candidates" / "discovered.json").read_text(encoding="utf-8"))
            self.assertEqual(pool["candidates"], [])

    def test_ingest_candidate_rejects_duplicate_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_index(root)
            write_candidate_pool(root)
            first = run_script(
                INGEST_SCRIPT,
                root,
                "--candidate-id",
                "github:acme/agent-skills:skills/python-review",
                "--namespace",
                "community",
                "--version",
                "0.1.0",
                "--description",
                "Reviews Python code.",
                "--targets",
                "codex",
                "--maintainer",
                "acme",
            )
            write_candidate_pool(root)

            second = run_script(
                INGEST_SCRIPT,
                root,
                "--candidate-id",
                "github:acme/agent-skills:skills/python-review",
                "--namespace",
                "community",
                "--version",
                "0.1.0",
                "--description",
                "Reviews Python code.",
                "--targets",
                "codex",
                "--maintainer",
                "acme",
            )

            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertEqual(second.returncode, 1, second.stdout + second.stderr)
            self.assertIn("source already exists", second.stderr)

    def test_promote_trust_requires_review_metadata_for_curated_or_official(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_index(root)
            write_candidate_pool(root)
            ingest = run_script(
                INGEST_SCRIPT,
                root,
                "--candidate-id",
                "github:acme/agent-skills:skills/python-review",
                "--namespace",
                "community",
                "--version",
                "0.1.0",
                "--description",
                "Reviews Python code.",
                "--targets",
                "codex",
                "--maintainer",
                "acme",
            )

            missing_review = run_script(
                PROMOTE_SCRIPT,
                root,
                "--identity",
                "community/python-review",
                "--level",
                "curated",
            )
            promoted = run_script(
                PROMOTE_SCRIPT,
                root,
                "--identity",
                "community/python-review",
                "--level",
                "curated",
                "--reviewer",
                "CassianFlorin",
                "--reviewed-at",
                "2026-06-23",
                "--featured",
                "--generated-at",
                "2026-06-23T00:00:00Z",
            )

            self.assertEqual(ingest.returncode, 0, ingest.stdout + ingest.stderr)
            self.assertEqual(missing_review.returncode, 1, missing_review.stdout + missing_review.stderr)
            self.assertIn("reviewer and reviewed_at are required", missing_review.stderr)
            self.assertEqual(promoted.returncode, 0, promoted.stdout + promoted.stderr)
            index = json.loads((root / "skillhub.index.json").read_text(encoding="utf-8"))
            entry = index["skills"][0]
            self.assertEqual(
                entry["trust"],
                {"level": "curated", "reviewer": "CassianFlorin", "reviewed_at": "2026-06-23"},
            )
            self.assertTrue(entry["featured"])
            self.assertEqual(index["generated_at"], "2026-06-23T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
