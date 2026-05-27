# Runtime Adapter

Use this skill when adding or reviewing support for a new agent runtime deployment target.

## Instructions

- Define the runtime name, environment variable, and default install directory first.
- Make deploy, dry-run, status, and uninstall behavior consistent with existing runtimes.
- Update supported target validation before publishing registry entries for the runtime.
- Add tests for explicit deploy, batch deploy, unsupported target handling, and status output.
- Keep runtime-specific behavior inside the deploy adapter boundary.

## Verification

```bash
go test ./...
skillhub deploy <runtime> --dry-run
skillhub deploy status <runtime>
```
