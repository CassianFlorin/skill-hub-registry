# Skill Metadata Quality

Use this skill when reviewing or improving `skill.yaml` and `skillhub.index.json` metadata.

## Instructions

- Keep identity, namespace, name, version, description, targets, and tags consistent.
- Prefer short descriptions that include the user task and domain.
- Use tags that help discovery rather than internal implementation labels.
- Require maintainers, license, trust level, and review fields for public catalog entries.
- Run registry validation before committing metadata changes.

## Verification

```bash
python3 scripts/validate_registry.py
skillhub registry index validate hub
skillhub catalog tags --registry hub
```
