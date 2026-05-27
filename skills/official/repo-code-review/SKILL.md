# Repo Code Review

Use this skill when reviewing code changes before merge, release, or handoff.

## Instructions

- Start with the diff and changed files, not a broad rewrite of the project.
- Prioritize bugs, regressions, security risks, data loss risks, and missing tests.
- Cite concrete files, functions, commands, or test cases for every finding.
- Separate findings from style opinions.
- If no serious issue is found, state that clearly and call out residual test gaps.
- Do not rewrite code during review unless the user explicitly asks for fixes.

## Review Order

1. Public behavior and compatibility.
2. Error handling and edge cases.
3. Data persistence, filesystem, network, or external side effects.
4. Test coverage for the changed behavior.
5. Release or migration risks.

## Output Shape

- Findings, ordered by severity.
- Open questions or assumptions.
- Verification checked.
- Short change summary, only after findings.
