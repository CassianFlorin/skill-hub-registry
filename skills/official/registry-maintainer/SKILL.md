# Registry Maintainer

Use this skill when adding, updating, validating, or reviewing entries in a `skill-hub` registry.

## Instructions

- Keep `skillhub.index.json` and each package `skill.yaml` aligned.
- Every registry-local source path must stay relative and point to a directory with `SKILL.md`.
- Use stable identities in `namespace/name` form.
- Set `targets` only to runtimes the skill is actually written for.
- Featured entries must have useful descriptions, tags, and review metadata.
- Run registry validation and a real install smoke test before publishing.

## Required Checks

```bash
skillhub registry add local hub <registry-path>
skillhub registry sync hub
skillhub registry index validate hub
skillhub catalog featured --registry hub
skillhub install hub/<identity>
```

## Review Focus

- Duplicate identities.
- Stale versions.
- Broken source paths.
- Vague descriptions.
- Private content in public skills.
