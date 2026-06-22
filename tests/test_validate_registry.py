import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "validate_registry.py"


def write_skill(root: Path, namespace: str, name: str, *, targets=None) -> str:
    targets = targets or ["codex"]
    skill_dir = root / "skills" / namespace / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\n---\n\n# {name}\n",
        encoding="utf-8",
    )
    target_lines = "\n".join(f"  - {target}" for target in targets)
    (skill_dir / "skill.yaml").write_text(
        textwrap.dedent(
            f"""\
            name: {name}
            namespace: {namespace}
            version: 0.1.0
            description: Test skill {name}.
            entry: SKILL.md
            targets:
            {target_lines}
            tags:
              - test
            author: Example
            """
        ),
        encoding="utf-8",
    )
    return f"skills/{namespace}/{name}"


def write_index(root: Path, skills: list[dict], *, schema_version: str = "2") -> None:
    (root / "skillhub.index.json").write_text(
        json.dumps(
            {
                "schema_version": schema_version,
                "registry": "hub",
                "generated_at": "2026-05-27T00:00:00Z",
                "skills": skills,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def valid_entry(namespace: str, name: str, source_path: str, *, targets=None) -> dict:
    return {
        "identity": f"{namespace}/{name}",
        "name": name,
        "namespace": namespace,
        "version": "0.1.0",
        "description": f"Test skill {name}.",
        "targets": targets or ["codex"],
        "tags": ["test"],
        "source": {"type": "registry", "path": source_path},
        "maintainers": ["Example"],
        "license": "MIT",
        "trust": {
            "level": "official",
            "reviewed_at": "2026-05-27",
            "reviewer": "Example",
        },
        "featured": True,
        "updated_at": "2026-05-27",
    }


def run_validator(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class ValidateRegistryTest(unittest.TestCase):
    def test_valid_registry_local_skill_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_path = write_skill(root, "official", "demo")
            write_index(root, [valid_entry("official", "demo", source_path)])

            result = run_validator(root)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("registry validation passed: 1 skills", result.stdout)

    def test_valid_registry_accepts_gemini_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_path = write_skill(root, "official", "gemini-demo", targets=["gemini"])
            write_index(root, [valid_entry("official", "gemini-demo", source_path, targets=["gemini"])])

            result = run_validator(root)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("registry validation passed: 1 skills", result.stdout)

    def test_validator_reports_multiple_registry_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_path = write_skill(root, "official", "demo")
            bad_entry = valid_entry("official", "demo", source_path)
            bad_entry["targets"] = ["codex", "unknown-runtime"]
            duplicate_entry = valid_entry("official", "demo", "../outside")
            duplicate_entry["featured"] = True
            duplicate_entry["trust"] = {"level": "community"}
            write_index(root, [bad_entry, duplicate_entry], schema_version="1")

            result = run_validator(root)

        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 1)
        self.assertIn("schema_version must be 2", output)
        self.assertIn("duplicate identity: official/demo", output)
        self.assertIn("unsupported target: unknown-runtime", output)
        self.assertIn("source.path escapes registry root", output)
        self.assertIn("featured skills require trust.reviewer", output)
        self.assertIn("featured skills require trust.reviewed_at", output)

    def test_external_git_source_does_not_require_local_skill_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = valid_entry("community", "remote-demo", "remote-demo")
            entry["trust"] = {"level": "community"}
            entry["featured"] = False
            entry["source"] = {
                "type": "git",
                "url": "https://github.com/example/skills.git",
                "path": "remote-demo",
                "ref": "v0.1.0",
                "sync_metadata": False,
            }
            write_index(root, [entry])

            result = run_validator(root)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("registry validation passed: 1 skills", result.stdout)

    def test_current_repository_validates(self) -> None:
        result = run_validator(REPO_ROOT)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("registry validation passed: 28 skills", result.stdout)

        index = json.loads((REPO_ROOT / "skillhub.index.json").read_text(encoding="utf-8"))
        identities = {entry["identity"] for entry in index["skills"]}
        self.assertIn("official/feishu-cli", identities)


if __name__ == "__main__":
    unittest.main()
