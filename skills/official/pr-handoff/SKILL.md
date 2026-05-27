# PR Handoff

Use this skill when preparing a pull request, merge request, or final implementation handoff.

## Instructions

- Inspect the current diff and recent commits.
- Summarize what changed in user-facing terms.
- List verification commands that were actually run and their outcomes.
- Call out migrations, release steps, or manual follow-ups.
- Do not claim tests passed unless the command output was checked in the current session.
- Keep the handoff short enough for reviewers to scan.

## Output Shape

```markdown
## Summary
- Change 1
- Change 2

## Verification
- `command`: result

## Notes
- Risk or follow-up
```

If there are no notes, omit the Notes section.
