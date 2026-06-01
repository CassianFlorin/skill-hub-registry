# skill-hub-registry

Official catalog registry for `skill-hub`.

This repository is consumed by:

```bash
skillhub init
skillhub registry sync hub
skillhub catalog featured
skillhub catalog list --registry hub
skillhub install hub/official/skill-authoring-guide
```

Registry entries use `skillhub.index.json` schema version `2`.

## Layout

```text
skillhub.index.json
skills/
  official/
    skill-authoring-guide/
    obsidian-workflow/
    git-commit-cn/
    feishu-cli/
    repo-code-review/
    systematic-debugging/
    release-readiness/
    public-repo-hygiene/
    registry-maintainer/
    go-cli-development/
    pr-handoff/
    marketplace-catalog/
    runtime-adapter/
    skill-metadata-quality/
```

## Validation

Run validation with a local `skillhub` binary:

```bash
python3 -m unittest tests/test_validate_registry.py
python3 scripts/validate_registry.py

registry_root="$(pwd)"
tmp="$(mktemp -d)"
export SKILLHUB_HOME="$tmp/home"
mkdir -p "$tmp/project"
cd "$tmp/project"
skillhub init
skillhub registry add local hub "$registry_root"
skillhub registry sync hub
skillhub registry index validate hub
skillhub catalog list --registry hub
skillhub catalog featured --registry hub
```

## Adding A Skill

1. Create a directory under `skills/<namespace>/<name>/`.
2. Add `SKILL.md` as the runtime entrypoint.
3. Add `skill.yaml` with `name`, `namespace`, `version`, `description`, `entry`, `targets`, `tags`, and `author`.
4. Add or update the matching entry in `skillhub.index.json`.
5. Run the validation commands above before opening a pull request.

For registry-local skills, the index `identity` must equal `<namespace>/<name>`, and `source.path` must stay inside this repository.

## Trust Levels

- `official`: maintained and reviewed by the registry maintainers.
- `curated`: reviewed by maintainers but owned outside the official set.
- `community`: submitted by the community with basic structural validation.
- `private`: intended for private use, not for broad public discovery.
- `unknown`: source exists but has not been reviewed.

Featured skills should be reviewed, useful to a broad audience, and have `trust.reviewer` plus `trust.reviewed_at` in the index.

## Public Repository Hygiene

Do not include private notes, local-only paths, secrets, internal URLs, or design-only artifacts. Keep public guidance operational: README updates, PR templates, validation scripts, and skill packages are acceptable; design plans belong outside this repository.
