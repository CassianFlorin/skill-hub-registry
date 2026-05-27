# Release Readiness

Use this skill when preparing a tag, package, deployment, or public release.

## Instructions

- Confirm the branch, remote, latest commit, and working tree state.
- Run the project verification commands from the repository, not from memory.
- Inspect release automation before triggering it.
- Prefer annotated tags when the project already uses them.
- After pushing, watch CI or release workflows to completion.
- Verify the final release page, packages, checksums, or deployment URL.

## Checklist

- Working tree is clean or intentionally dirty.
- Required tests and build commands passed.
- Version, tag, or release notes match the intended commit.
- Remote workflow completed successfully.
- Artifacts are present and named as expected.

## Output Shape

- Release identifier.
- Commit.
- Verification commands.
- CI or deployment result.
- Artifact list.
