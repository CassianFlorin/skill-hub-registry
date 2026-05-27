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
    repo-code-review/
    systematic-debugging/
    release-readiness/
    public-repo-hygiene/
    registry-maintainer/
    go-cli-development/
    pr-handoff/
```

## Validation

Run validation with a local `skillhub` binary:

```bash
skillhub registry add local hub .
skillhub registry sync hub
skillhub catalog featured --registry hub
```
