# Systematic Debugging

Use this skill when a command, test, build, service, or user workflow is failing.

## Instructions

- Reproduce the exact symptom before proposing a fix.
- Capture the failing command, input, output, and environment assumptions.
- Trace from the symptom to the responsible code or configuration boundary.
- Form one hypothesis at a time and choose the smallest check that can disprove it.
- Change code only after the evidence points to a specific cause.
- After fixing, rerun the original failing check and a focused regression check.

## Common Mistakes

- Treating a nearby warning as the root cause.
- Fixing code that was not exercised by the failing path.
- Using a broad green test suite as proof that the original symptom is fixed.
- Hiding uncertainty instead of naming the missing evidence.

## Output Shape

- Symptom reproduced.
- Evidence trail.
- Root cause.
- Fix.
- Verification.
