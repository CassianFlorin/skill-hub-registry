# Go CLI Development

Use this skill when changing a Go command-line application.

## Instructions

- Start from the command behavior and its tests.
- Prefer table-driven tests for parser, filter, and formatter behavior.
- Keep command output stable and easy to parse.
- Return errors from command handlers instead of exiting deep in library code.
- Use `gofmt` before final verification.
- Run targeted tests first, then the full suite and build.

## Verification

```bash
go test ./...
go build -v ./cmd/<binary>
git diff --check
```

## Output Design

- Use tabs for machine-readable list output.
- Include enough fields for users to decide the next command.
- Keep detailed metadata in `info` commands rather than crowded list views.
