# Feishu CLI

Use this skill when a user asks to install, configure, authenticate, verify, or use Feishu/Lark CLI capabilities from an Agent workflow.

Source: https://open.feishu.cn/document/no_class/mcp-archive/feishu-cli-installation-guide.md

## When To Use

- The user asks to set up Feishu CLI or the Feishu CLI companion Skill.
- The task needs access to Feishu/Lark documents, sheets, messages, apps, or Open Platform operations through `lark-cli`.
- The user asks whether Feishu CLI is authenticated, configured, or ready for Agent use.

## Setup

First check whether the CLI is already available:

```bash
lark-cli auth status
```

If `lark-cli` is missing, install the CLI and the official companion Skill:

```bash
npm install -g @larksuite/cli
npx -y skills add https://open.feishu.cn --skill -y
```

Configure application credentials:

```bash
lark-cli config init --new
```

This may require user-provided app credentials. Do not invent credentials or write secrets into repository files.

## Login

Start login and share the authorization URL with the user:

```bash
lark-cli auth login --recommend
```

The user must complete authorization in a browser. After they finish, verify the session:

```bash
lark-cli auth status
```

## Operating Rules

- Prefer `lark-cli` for Feishu/Lark operations after authentication is verified.
- Run read/status commands before mutating Feishu resources.
- Confirm with the user before sending messages, editing shared documents, changing permissions, or deleting content.
- Keep app IDs, app secrets, tenant credentials, tokens, and authorization URLs out of committed files and public logs.
- If a command fails, report the command, exit status, and actionable next step instead of retrying blindly.

## Verification

```bash
lark-cli auth status
lark-cli config list
```

If either command is unavailable, reinstall the CLI and companion Skill using the setup commands above.
