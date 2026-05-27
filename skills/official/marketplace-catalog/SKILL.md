# Marketplace Catalog

Use this skill when creating or reviewing a public catalog page for installable skills.

## Instructions

- Start from `skillhub.index.json` instead of hand-maintained catalog content.
- Preserve registry identity as the canonical install reference.
- Show runtime targets, tags, trust level, version, maintainers, and license.
- Keep install commands visible near each skill.
- Prefer static output that can be generated in CI and reviewed in a pull request.

## Verification

```bash
skillhub catalog list --json
skillhub catalog tags --json
skillhub catalog targets --json
```
