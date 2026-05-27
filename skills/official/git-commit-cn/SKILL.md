# Git Commit CN

Use this skill when preparing a Chinese Git commit message.

## Instructions

- Inspect staged changes first with `git diff --cached`.
- If nothing is staged, inspect unstaged changes with `git diff`.
- Check recent style with `git log --oneline -5`.
- Use this format:

```text
<type>(<module>): 简短描述

- 修改点1
- 修改点2
- 修改点3
```

- Keep the summary under 50 Chinese characters.
- Use one of: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `chore`.
- If changes are unrelated, recommend splitting commits.
