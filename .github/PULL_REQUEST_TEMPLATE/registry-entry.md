## Registry Entry Checklist

- [ ] `skillhub.index.json` uses schema version `2`.
- [ ] This PR is adding or updating: `namespace/name`.
- [ ] Skill identity is stable and namespaced as `namespace/name`.
- [ ] Registry-local skills include both `SKILL.md` and `skill.yaml`.
- [ ] `skill.yaml` metadata matches the index entry.
- [ ] Source path stays inside this repository, or the external source URL is public and intentional.
- [ ] Runtime targets are declared and limited to supported runtimes.
- [ ] Trust level is one of `official`, `curated`, `community`, `private`, `unknown`.
- [ ] License and maintainer information are included.
- [ ] Featured status is intentional and reviewed.
- [ ] This PR does not include private notes, local-only paths, secrets, internal URLs, or design-only artifacts.

## Skill Metadata

- Identity:
- Runtime targets:
- Trust level:
- Maintainer:
- License:
- Source type: `registry` / external
- Featured: yes / no

## Featured Rationale

If this skill should be featured, explain why it is broadly useful and ready for higher visibility.

## Verification

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
```
