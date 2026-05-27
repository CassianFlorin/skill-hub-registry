# Skill Authoring Guide

Use this skill when creating or reviewing a `skill-hub` compatible skill package.

## Instructions

- Keep the skill focused on one repeatable workflow.
- Put durable instructions in `SKILL.md`.
- Put reusable examples, checklists, or scripts under `references/`, `scripts/`, or `assets/`.
- Include a `skill.yaml` with name, namespace, version, description, entry, targets, and tags.
- Prefer small, testable workflows over broad general-purpose prompts.
- Before publishing, install the skill locally and verify its entry file can be deployed to the intended runtime.

## Checklist

- The skill has a clear trigger.
- The instructions tell the agent what to do and what not to do.
- The package avoids private credentials and local-only paths.
- The version is updated when behavior changes.
