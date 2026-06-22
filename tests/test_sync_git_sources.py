import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "sync_git_sources.py"


def git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
    )


def write_remote_skill(root: Path, relative_path: str) -> None:
    skill_dir = root / relative_path
    skill_dir.mkdir(parents=True)
    (skill_dir / "skill.yaml").write_text(
        textwrap.dedent(
            """\
            name: remote-demo
            namespace: community
            version: 0.2.0
            description: Fresh remote skill metadata.
            entry: SKILL.md
            targets:
              - codex
              - claude
            tags:
              - remote
              - sync
            author: Remote Maintainer
            """
        ),
        encoding="utf-8",
    )
    (skill_dir / "SKILL.md").write_text(
        "# Remote Demo\n\nFresh remote skill body.\n",
        encoding="utf-8",
    )


def write_registry_index(root: Path, remote_url: str) -> None:
    (root / "skillhub.index.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "registry": "hub",
                "generated_at": "2026-06-01T00:00:00Z",
                "skills": [
                    {
                        "identity": "community/remote-demo",
                        "name": "remote-demo",
                        "namespace": "community",
                        "version": "0.1.0",
                        "description": "Stale local metadata.",
                        "targets": ["codex"],
                        "tags": ["stale"],
                        "source": {
                            "type": "git",
                            "url": remote_url,
                            "path": "skills/remote-demo",
                        },
                        "maintainers": ["Old Maintainer"],
                        "license": "MIT",
                        "trust": {"level": "community"},
                        "featured": False,
                        "updated_at": "2026-06-01",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def run_sync(root: Path, cache_dir: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(root),
            "--cache-dir",
            str(cache_dir),
            "--updated-at",
            "2026-06-02",
            "--generated-at",
            "2026-06-02T00:00:00Z",
            *extra_args,
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class SyncGitSourcesTest(unittest.TestCase):
    def test_sync_git_sources_refreshes_catalog_metadata_from_remote_skill_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            registry_root = workspace / "registry"
            remote_root = workspace / "remote"
            cache_dir = workspace / "cache"
            registry_root.mkdir()
            write_remote_skill(remote_root, "skills/remote-demo")
            git(remote_root, "init")
            git(remote_root, "config", "user.email", "skillhub@example.com")
            git(remote_root, "config", "user.name", "SkillHub Test")
            git(remote_root, "add", ".")
            git(remote_root, "commit", "-m", "initial remote skill")
            write_registry_index(registry_root, str(remote_root))

            result = run_sync(registry_root, cache_dir)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("updated community/remote-demo", result.stdout)
            index = json.loads((registry_root / "skillhub.index.json").read_text(encoding="utf-8"))
            skill = index["skills"][0]
            self.assertEqual(index["generated_at"], "2026-06-02T00:00:00Z")
            self.assertEqual(skill["version"], "0.2.0")
            self.assertEqual(skill["description"], "Fresh remote skill metadata.")
            self.assertEqual(skill["targets"], ["codex", "claude"])
            self.assertEqual(skill["tags"], ["remote", "sync"])
            self.assertEqual(skill["maintainers"], ["Remote Maintainer"])
            self.assertEqual(skill["updated_at"], "2026-06-02")
            self.assertTrue(skill["checksum"].startswith("sha256:"))
            self.assertEqual(skill["source"]["url"], str(remote_root))
            self.assertNotIn("ref", skill["source"])

    def test_sync_git_sources_writes_summary_json_for_automation_prs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            registry_root = workspace / "registry"
            remote_root = workspace / "remote"
            cache_dir = workspace / "cache"
            summary_path = workspace / "summary.json"
            registry_root.mkdir()
            write_remote_skill(remote_root, "skills/remote-demo")
            git(remote_root, "init")
            git(remote_root, "config", "user.email", "skillhub@example.com")
            git(remote_root, "config", "user.name", "SkillHub Test")
            git(remote_root, "add", ".")
            git(remote_root, "commit", "-m", "initial remote skill")
            write_registry_index(registry_root, str(remote_root))

            result = run_sync(registry_root, cache_dir, "--summary-json", str(summary_path))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["changed_count"], 1)
            self.assertEqual(summary["unchanged_count"], 0)
            self.assertEqual(len(summary["changed"]), 1)
            change = summary["changed"][0]
            self.assertEqual(change["identity"], "community/remote-demo")
            self.assertEqual(change["source_url"], str(remote_root))
            self.assertEqual(change["source_path"], "skills/remote-demo")
            self.assertEqual(change["old_version"], "0.1.0")
            self.assertEqual(change["new_version"], "0.2.0")
            self.assertIsNone(change["old_checksum"])
            self.assertTrue(change["new_checksum"].startswith("sha256:"))
            self.assertIn("version", change["changed_fields"])
            self.assertIn("checksum", change["changed_fields"])

    def test_sync_git_sources_records_failures_and_continues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            registry_root = workspace / "registry"
            remote_root = workspace / "remote"
            cache_dir = workspace / "cache"
            summary_path = workspace / "summary.json"
            registry_root.mkdir()
            write_remote_skill(remote_root, "skills/remote-demo")
            git(remote_root, "init")
            git(remote_root, "config", "user.email", "skillhub@example.com")
            git(remote_root, "config", "user.name", "SkillHub Test")
            git(remote_root, "add", ".")
            git(remote_root, "commit", "-m", "initial remote skill")
            index = {
                "schema_version": "2",
                "registry": "hub",
                "generated_at": "2026-06-01T00:00:00Z",
                "skills": [
                    {
                        "identity": "community/missing-demo",
                        "name": "missing-demo",
                        "namespace": "community",
                        "version": "0.1.0",
                        "description": "Broken remote metadata.",
                        "targets": ["codex"],
                        "tags": ["broken"],
                        "source": {
                            "type": "git",
                            "url": str(remote_root),
                            "path": "skills/missing-demo",
                        },
                        "maintainers": ["Old Maintainer"],
                        "license": "MIT",
                        "trust": {"level": "community"},
                        "featured": False,
                        "updated_at": "2026-06-01",
                    },
                    {
                        "identity": "community/remote-demo",
                        "name": "remote-demo",
                        "namespace": "community",
                        "version": "0.1.0",
                        "description": "Stale local metadata.",
                        "targets": ["codex"],
                        "tags": ["stale"],
                        "source": {
                            "type": "git",
                            "url": str(remote_root),
                            "path": "skills/remote-demo",
                        },
                        "maintainers": ["Old Maintainer"],
                        "license": "MIT",
                        "trust": {"level": "community"},
                        "featured": False,
                        "updated_at": "2026-06-01",
                    },
                ],
            }
            (registry_root / "skillhub.index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")

            result = run_sync(registry_root, cache_dir, "--summary-json", str(summary_path))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["changed_count"], 1)
            self.assertEqual(summary["failed_count"], 1)
            self.assertEqual(summary["failed"][0]["identity"], "community/missing-demo")
            self.assertIn("missing remote skill.yaml", summary["failed"][0]["error"])
            updated = json.loads((registry_root / "skillhub.index.json").read_text(encoding="utf-8"))
            self.assertEqual(updated["skills"][1]["version"], "0.2.0")

    def test_sync_git_sources_skips_manual_metadata_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            registry_root = workspace / "registry"
            remote_root = workspace / "remote"
            cache_dir = workspace / "cache"
            summary_path = workspace / "summary.json"
            registry_root.mkdir()
            write_registry_index(registry_root, str(remote_root))
            index = json.loads((registry_root / "skillhub.index.json").read_text(encoding="utf-8"))
            index["skills"][0]["source"]["sync_metadata"] = False
            (registry_root / "skillhub.index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")

            result = run_sync(registry_root, cache_dir, "--summary-json", str(summary_path))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["changed_count"], 0)
            self.assertEqual(summary["failed_count"], 0)
            self.assertEqual(summary["skipped_count"], 1)
            self.assertEqual(summary["skipped"][0]["identity"], "community/remote-demo")
            self.assertIn("sync_metadata", summary["skipped"][0]["reason"])

    def test_check_mode_reports_stale_git_source_metadata_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            registry_root = workspace / "registry"
            remote_root = workspace / "remote"
            cache_dir = workspace / "cache"
            registry_root.mkdir()
            write_remote_skill(remote_root, "skills/remote-demo")
            git(remote_root, "init")
            git(remote_root, "config", "user.email", "skillhub@example.com")
            git(remote_root, "config", "user.name", "SkillHub Test")
            git(remote_root, "add", ".")
            git(remote_root, "commit", "-m", "initial remote skill")
            write_registry_index(registry_root, str(remote_root))

            result = run_sync(registry_root, cache_dir, "--check")

            self.assertEqual(result.returncode, 1)
            self.assertIn("out of sync: community/remote-demo", result.stderr)
            index = json.loads((registry_root / "skillhub.index.json").read_text(encoding="utf-8"))
            self.assertEqual(index["skills"][0]["version"], "0.1.0")


if __name__ == "__main__":
    unittest.main()
