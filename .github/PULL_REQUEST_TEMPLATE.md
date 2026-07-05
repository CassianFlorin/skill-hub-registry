## Skill submission

<!-- Delete this section if the PR is not a Skill submission. -->

- Identity: `<namespace>/<name>`
- Source type: registry-hosted / git-sourced
- What the Skill does:
- Agents tested with: <!-- e.g. Codex, Claude -->

## Checklist

- [ ] `python3 scripts/validate_registry.py` passes locally
- [ ] `python3 scripts/scan_registry.py` reports no medium/high findings
- [ ] Index entry `trust.level` is `community` and `featured` is `false` (maintainers promote later)
- [ ] For git sources: `ref` is pinned to a tag or commit SHA
