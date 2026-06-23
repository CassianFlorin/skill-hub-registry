#!/usr/bin/env python3
"""Scan a skill-hub registry for security and quality risks."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


ALLOWED_LICENSES = {
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "CC0-1.0",
}
SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3}
TEXT_EXTENSIONS = {
    ".md",
    ".markdown",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".rb",
    ".go",
    ".rs",
}


class PatternRule:
    def __init__(self, category: str, severity: str, name: str, pattern: str, message: str, flags: int = re.IGNORECASE) -> None:
        self.category = category
        self.severity = severity
        self.name = name
        self.pattern = re.compile(pattern, flags)
        self.message = message


SECRET_RULES = [
    PatternRule("secret", "high", "aws-access-key", r"\bAKIA[0-9A-Z]{16}\b", "possible AWS access key"),
    PatternRule("secret", "high", "github-token", r"\bgh[pousr]_[A-Za-z0-9_]{8,}\b", "possible GitHub token"),
    PatternRule("secret", "high", "openai-api-key", r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{8,}\b", "possible OpenAI-style API key"),
    PatternRule("secret", "high", "slack-token", r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b", "possible Slack token"),
    PatternRule("secret", "high", "private-key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key material"),
    PatternRule("secret", "medium", "credential-assignment", r"\b(password|api[_-]?key|secret|token)\s*=\s*['\"]?[^\s'\"]{8,}", "possible hardcoded credential"),
]

PROMPT_INJECTION_RULES = [
    PatternRule("prompt-injection", "medium", "ignore-instructions", r"ignore (all )?(previous|prior|above) instructions", "instruction override language"),
    PatternRule("prompt-injection", "medium", "role-reset", r"you are now|act as (a )?system|new system prompt", "role/system prompt override language"),
    PatternRule("prompt-injection", "medium", "secret-exfiltration", r"read ~/.ssh|read ~/.env|exfiltrate|send secrets", "secret exfiltration language"),
]

SHELL_RISK_RULES = [
    PatternRule("shell-risk", "high", "curl-pipe-shell", r"\b(curl|wget)\b[^\n|]*\|\s*(sh|bash|zsh|fish)\b", "network download piped to shell"),
    PatternRule("shell-risk", "high", "destructive-rm", r"\brm\s+-rf\s+(/|~|\$HOME|\.\.)", "potentially destructive recursive deletion"),
    PatternRule("shell-risk", "medium", "eval", r"\beval\s*(\(|\s)", "dynamic eval usage"),
    PatternRule("shell-risk", "medium", "chmod-777", r"\bchmod\s+777\b", "overly broad file permissions"),
    PatternRule("shell-risk", "medium", "sudo", r"\bsudo\b", "privileged command usage"),
    PatternRule("shell-risk", "medium", "base64-shell", r"base64\s+(-d|--decode)[^\n|]*\|\s*(sh|bash|zsh|fish)\b", "encoded payload executed by shell"),
]

ALL_RULES = SECRET_RULES + PROMPT_INJECTION_RULES + SHELL_RISK_RULES


def is_text_file(path: Path) -> bool:
    return path.name in {"SKILL.md", "skill.yaml"} or path.suffix.lower() in TEXT_EXTENSIONS


def load_index(root: Path) -> dict[str, Any]:
    return json.loads((root / "skillhub.index.json").read_text(encoding="utf-8"))


def safe_registry_path(root: Path, source_path: str) -> Path | None:
    candidate = (root / source_path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def iter_skill_files(skill_dir: Path) -> Iterable[Path]:
    for path in sorted(skill_dir.rglob("*")):
        if path.is_file() and is_text_file(path):
            yield path


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def add_finding(
    findings: list[dict[str, Any]],
    *,
    identity: str,
    category: str,
    severity: str,
    message: str,
    file: str | None = None,
    line: int | None = None,
    rule: str | None = None,
) -> None:
    finding: dict[str, Any] = {
        "identity": identity,
        "category": category,
        "severity": severity,
        "message": message,
    }
    if file is not None:
        finding["file"] = file
    if line is not None:
        finding["line"] = line
    if rule is not None:
        finding["rule"] = rule
    findings.append(finding)


def scan_text(identity: str, rel_file: str, text: str, findings: list[dict[str, Any]]) -> None:
    for rule in ALL_RULES:
        for match in rule.pattern.finditer(text):
            add_finding(
                findings,
                identity=identity,
                category=rule.category,
                severity=rule.severity,
                message=rule.message,
                file=rel_file,
                line=line_number(text, match.start()),
                rule=rule.name,
            )


def scan_license(entry: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    identity = str(entry.get("identity", "unknown"))
    license_value = entry.get("license")
    if not isinstance(license_value, str) or not license_value.strip():
        add_finding(
            findings,
            identity=identity,
            category="license",
            severity="medium",
            message="missing license",
            rule="missing-license",
        )
        return
    if license_value not in ALLOWED_LICENSES:
        add_finding(
            findings,
            identity=identity,
            category="license",
            severity="medium",
            message=f"license is not in allowlist: {license_value}",
            rule="unsupported-license",
        )


def scan_registry(root: Path) -> dict[str, Any]:
    root = root.resolve()
    index = load_index(root)
    findings: list[dict[str, Any]] = []
    scanned_skills = 0
    skipped_external = 0

    for entry in index.get("skills", []):
        if not isinstance(entry, dict):
            continue
        identity = str(entry.get("identity", "unknown"))
        scanned_skills += 1
        scan_license(entry, findings)

        source = entry.get("source", {})
        if not isinstance(source, dict) or source.get("type") != "registry":
            skipped_external += 1
            continue
        source_path = source.get("path")
        if not isinstance(source_path, str):
            continue
        skill_dir = safe_registry_path(root, source_path)
        if skill_dir is None or not skill_dir.is_dir():
            continue
        for file_path in iter_skill_files(skill_dir):
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            scan_text(identity, str(file_path.relative_to(root)), text, findings)

    summary = {severity: 0 for severity in ("high", "medium", "low")}
    for finding in findings:
        summary[finding["severity"]] += 1
    return {
        "summary": summary,
        "scanned_skills": scanned_skills,
        "skipped_external_sources": skipped_external,
        "findings": findings,
    }


def finding_exceeds_threshold(finding: dict[str, Any], threshold: str) -> bool:
    return SEVERITY_ORDER[finding["severity"]] >= SEVERITY_ORDER[threshold]


def print_report(report: dict[str, Any]) -> None:
    summary = report["summary"]
    findings = report["findings"]
    if not findings:
        print(
            "registry scan passed: "
            f"{report['scanned_skills']} skills, "
            f"{report['skipped_external_sources']} external sources skipped"
        )
        return
    print(
        "registry scan findings: "
        f"high={summary['high']} medium={summary['medium']} low={summary['low']}"
    )
    for finding in findings:
        location = ""
        if finding.get("file"):
            location = f" {finding['file']}:{finding.get('line', 1)}"
        print(
            f"[{finding['severity']}] {finding['category']} {finding['identity']}{location}: {finding['message']}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan a skill-hub registry for security and quality risks.")
    parser.add_argument("--root", default=".", help="Registry repository root.")
    parser.add_argument("--report-json", help="Write a JSON scan report.")
    parser.add_argument(
        "--fail-on",
        choices=("low", "medium", "high"),
        default="medium",
        help="Return non-zero when any finding has this severity or higher.",
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    report = scan_registry(root)
    if args.report_json:
        report_path = Path(args.report_json)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print_report(report)
    return 1 if any(finding_exceeds_threshold(finding, args.fail_on) for finding in report["findings"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
