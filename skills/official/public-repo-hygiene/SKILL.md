# Public Repo Hygiene

Use this skill when working in a public repository or preparing changes for public history.

## Instructions

- Inspect staged and unstaged changes before committing.
- Do not commit private planning notes, local vault exports, credentials, tokens, or machine-specific paths.
- Keep project design records outside the public repository when the user requests it.
- Add narrow `.gitignore` entries for generated local artifacts.
- If sensitive content has already been committed, stop normal work and plan a history rewrite before pushing more commits.
- Verify the final commit only contains intended public artifacts.

## Checks

```bash
git status --short
git diff --cached --stat
git diff --cached
git log --oneline -5
```

Search for obvious private material when risk is high:

```bash
rg -n "token|secret|password|PRIVATE|/Users/|Cassian Note|docs/" .
```
