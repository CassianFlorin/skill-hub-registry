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
python3 -m unittest tests/test_sync_git_sources.py
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

Registry entries can point to either a package stored in this repository or a package stored in an upstream git repository.

For registry-local skills:

1. Create a directory under `skills/<namespace>/<name>/`.
2. Add `SKILL.md` as the runtime entrypoint.
3. Add `skill.yaml` with `name`, `namespace`, `version`, `description`, `entry`, `targets`, `tags`, and `author`.
4. Add or update the matching entry in `skillhub.index.json`.
5. Run the validation commands above before opening a pull request.

For registry-local skills, the index `identity` must equal `<namespace>/<name>`, and `source.path` must stay inside this repository.

For git-backed skills:

1. Add an entry in `skillhub.index.json` with `source.type` set to `git`, `source.url` set to the upstream repository, and `source.path` set to the skill directory inside that repository.
2. Omit `source.ref` when the installed skill should follow the upstream default branch. Set `source.ref` to a tag or commit only when the catalog entry should stay pinned to a reviewed version.
3. Set `source.sync_metadata` to `false` for git-backed entries whose catalog metadata is maintained manually because the upstream directory does not contain SkillHub-style `skill.yaml` metadata.
4. Refresh catalog metadata from the upstream skill package:

```bash
python3 scripts/sync_git_sources.py
```

Use check mode in review or automation when the index should already match upstream metadata:

```bash
python3 scripts/sync_git_sources.py --check
```

Write a machine-readable sync summary for automation PR bodies:

```bash
python3 scripts/sync_git_sources.py --summary-json sync-summary.json
```

## Automated Registry Maintenance

Git-backed skill entries are maintained by the scheduled `Sync Git Sources` workflow. It runs daily and can also be started manually from GitHub Actions.

The workflow:

1. Runs `python3 scripts/sync_git_sources.py --summary-json sync-summary.json`.
2. Refreshes `skillhub.index.json` from upstream `skill.yaml` metadata when a git-backed skill changed.
3. Runs `python3 scripts/validate_registry.py`.
4. Skips entries marked with `source.sync_metadata: false`.
5. Opens or updates a pull request named `chore(registry): sync git-backed skill metadata` when the index changed.

The generated PR body lists each changed skill, old/new version, and changed metadata fields. Registry maintainers should review the upstream diff and merge the PR when the update is expected. New skills and trust-level promotions still require separate human-reviewed PRs.

## Trust Levels

- `official`: maintained and reviewed by the registry maintainers.
- `curated`: reviewed by maintainers but owned outside the official set.
- `community`: submitted by the community with basic structural validation.
- `private`: intended for private use, not for broad public discovery.
- `unknown`: source exists but has not been reviewed.

Featured skills should be reviewed, useful to a broad audience, and have `trust.reviewer` plus `trust.reviewed_at` in the index.

## Public Repository Hygiene

Do not include private notes, local-only paths, secrets, internal URLs, or design-only artifacts. Keep public guidance operational: README updates, PR templates, validation scripts, and skill packages are acceptable; design plans belong outside this repository.
