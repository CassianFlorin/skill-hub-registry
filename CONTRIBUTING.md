# Contributing a Skill

This registry is the default `hub` catalog for [skill-hub](https://github.com/CassianFlorin/skill-hub). Anyone can submit a Skill through a pull request. Every entry is validated in CI and reviewed before merge.

## Two Ways to List a Skill

**Registry-hosted** — the Skill files live in this repository under `skills/<namespace>/<name>/`. Best for new Skills that do not have their own repository.

**Git-sourced** — the Skill files stay in your repository; this registry only lists an index entry pointing at a pinned ref. Best when you maintain the Skill elsewhere and want the catalog to reference it.

## Submitting a Registry-Hosted Skill

1. Fork this repository.
2. Add your Skill under `skills/<namespace>/<name>/`. Use your GitHub username (or org) as the namespace — `official` is reserved for registry maintainers. Minimum layout:

   ```text
   skills/your-namespace/your-skill/
   ├── skill.yaml
   ├── SKILL.md
   └── references/        # optional supporting files
   ```

   Minimal `skill.yaml`:

   ```yaml
   name: your-skill
   namespace: your-namespace
   version: 0.1.0
   description: One-line description of what the Skill does.
   entry: SKILL.md
   targets:
     - codex
     - claude
   tags:
     - example
   author: your-namespace
   ```

3. Add an entry to `skillhub.index.json`:

   ```json
   {
     "identity": "your-namespace/your-skill",
     "name": "your-skill",
     "namespace": "your-namespace",
     "version": "0.1.0",
     "description": "One-line description of what the Skill does.",
     "targets": ["codex", "claude"],
     "tags": ["example"],
     "source": { "type": "registry", "path": "skills/your-namespace/your-skill" },
     "maintainers": ["your-github-username"],
     "license": "MIT",
     "trust": { "level": "community" },
     "featured": false,
     "updated_at": "YYYY-MM-DD"
   }
   ```

4. Validate locally (same checks CI runs):

   ```bash
   python3 scripts/validate_registry.py
   python3 scripts/scan_registry.py
   ```

5. Open a pull request describing what the Skill does and which agents you tested it with.

## Submitting a Git-Sourced Skill

Add only the index entry, with a `git` source pinned to a tag or commit:

```json
"source": {
  "type": "git",
  "url": "https://github.com/you/your-skills.git",
  "path": "skills/your-skill",
  "ref": "<tag-or-commit-sha>"
}
```

Pin `ref` to an immutable tag or commit SHA, not a branch, so installs stay reproducible. Your Skill repository must carry a license compatible with redistribution (the `license` field in the entry must match it).

## Trust Levels

| Level | Meaning | Who sets it |
| --- | --- | --- |
| `community` | Submitted by the community; validated by CI, not manually audited. | You, on submission. |
| `curated` | Reviewed by a registry maintainer for quality and safety. | Maintainers, with `reviewer` and `reviewed_at`. |
| `official` | Maintained by the registry team. | Maintainers only. |

New submissions start at `community`. Maintainers may promote entries later; `featured: true` requires a maintainer review, so leave it `false`.

## Review Criteria

- The Skill does what its description says, with no misleading claims.
- No malicious, destructive, or data-exfiltrating instructions or scripts. The CI security scanner flags risky patterns; flagged PRs get extra scrutiny.
- `skill.yaml` metadata matches the index entry (name, namespace, version, targets).
- Descriptions and tags are specific enough for `skillhub search` to find the Skill.

## Updating Your Skill

Bump `version` in `skill.yaml`, update the index entry's `version` and `updated_at` (and `ref` for git sources), and open a PR. Installed copies pick up the change through `skillhub check` / `skillhub update`.

## Reporting a Problematic Skill

Open an issue naming the Skill identity and the concern. Entries that turn out to be unsafe are removed or demoted.

## License

Registry metadata and registry-hosted Skills are published under the [MIT License](LICENSE) unless an entry states otherwise. Git-sourced Skills keep the license of their own repository.
