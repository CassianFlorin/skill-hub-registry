## Registry Entry Checklist

- [ ] `skillhub.index.json` uses schema version `2`.
- [ ] Skill identity is stable and namespaced.
- [ ] Source path or source URL is valid.
- [ ] Runtime targets are declared.
- [ ] Trust level is one of `official`, `curated`, `community`, `private`, `unknown`.
- [ ] License and maintainer information are included when applicable.
- [ ] Featured status is intentional.

## Verification

```bash
skillhub registry sync hub
skillhub catalog list --registry hub
```
