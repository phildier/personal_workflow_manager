---
name: pwm-workflow
description: Guides agents to run Personal Workflow Manager non-interactively for Jira issue-create flows (`pwm ic`), Jira work-start flows (`pwm ws`), and pull request flows (`pwm pr`). Use when automation must avoid interactive prompts.
license: Proprietary
compatibility: Agent Skills compatible clients.
metadata:
  owner: personal
  domain: developer-workflow
  maturity: beta
---

# PWM Workflow

## Purpose

Execute reliable, non-interactive `pwm ws`, `pwm ic`, and `pwm pr` workflows
with a default bias toward a single issue/branch/PR flow.

## Use This Skill When

- The user asks to create/start Jira work with `pwm ws` in automation.
- The user needs issue creation without branch changes via `pwm ic`.
- The user needs `pwm ws --new` without prompt collection.
- The user needs `pwm pr` creation in non-interactive sessions.
- The user asks to create/open a PR and expects completion in the same turn.

## Validate Context First

- Confirm you are in the target git repository.
- Confirm `pwm` is installed and available on `PATH`.

## Command Selection Policy

- Prefer `pwm ws --new` for standard new work so one command creates the issue
  and starts branch work.
- Use `pwm ic` only when issue-only creation is intentionally required, such as:
  dirty working tree, current branch should not change, or branch switching
  would conflict with existing local files.
- When the user asks to create an epic, use `pwm ic` with `--issue-type Epic`;
  do not use `--epic`, because epics are parent containers rather than children
  of another epic.
- After creating an issue with `pwm ic`, reuse that same issue key with
  `pwm ws <ISSUE-KEY>` instead of creating another issue.
- Keep one task to one ticket and one PR unless the user explicitly requests
  splitting work.
- When a user asks for a PR, finish checks/commit/push as needed and run the PR
  command in the same response. Do not ask for confirmation unless the user
  explicitly requested a diff review first or a command fails.

## Core Non-Interactive Commands

- Create and start a new Jira issue:
  - `pwm ws --new --non-interactive --summary "Implement feature X"`
- Create and start a new Jira issue with parent epic:
  - `pwm ws --new --non-interactive --summary "Implement feature X" --issue-type Task --epic ABC-100`
- Start existing Jira issue:
  - `pwm ws ABC-123 --no-transition --no-comment`
- Create Jira issue only (no branch changes, exception path):
  - `pwm ic --non-interactive --summary "Implement feature X" --issue-type Task`
- Create Jira issue only with parent epic (exception path):
  - `pwm ic --non-interactive --summary "Fix API bug" --issue-type Bug --epic ABC-100`
- Create Jira epic only:
  - `pwm ic --non-interactive --summary "Create feature area" --issue-type Epic --no-save-defaults`
- Create/open PR without interactive confirms or browser launch:
  - `pwm pr --non-interactive --no-open-browser --label ai-assisted`
- Create/open PR and apply labels (repeat `--label` as needed):
  - `pwm pr --non-interactive --no-open-browser --label bug --label ai-assisted`
- Read-only PR diagnostics:
  - `pwm pr --preflight --non-interactive --label ai-assisted`

## Required Inputs

- For `pwm ic --non-interactive`, always provide `--summary`.
- For `pwm ws --new --non-interactive`, always provide `--summary`.
- Provide `--issue-type`, `--labels`, `--story-points`, and repeatable
  `--custom-field KEY=VALUE` when project defaults are insufficient.
- `pwm ws --new` and `pwm ic` automatically apply matching entries from
  `~/.config/pwm/agent-defaults.toml` (keyed by Jira project and/or
  repository). Only pass explicit overrides when needed.
- Use `--epic ABC-123` to set parent epic for supported issue types:
  Story, Bug, Spike, Task, Incident.
- Use `--issue-type Epic` to create an epic. Do not combine it with `--epic`.
- Use `--save-defaults` or `--no-save-defaults` to avoid default-save prompts.
- `pwm ic` creates Jira issues only. It does not switch branches, transition
  issues, or post start-work comments.
- Use `--no-ai` when deterministic PR metadata is preferred.
- Use repeatable `--label` to apply labels to either an existing PR or a newly
  created PR; no labels are applied unless `--label` is provided.
- Use `--create-anyway` only when an intentionally no-ahead-commit PR is
  desired.
- Before re-running `pwm pr`, inspect `.git/pwm/pr.json` receipt. Re-run PR
  only when HEAD changed or requested PR metadata changed (for example labels).

## Label Selection Policy

- Add `--label ai-assisted` when the PR is adding code at 50% or more of the
  total code changes.
- Add `--label bug` when the user's prompt mentions "bug".
- Do not add any labels other than `ai-assisted` and `bug` unless the user
  explicitly asks.
- Do not create new labels; only use labels that already exist in the target
  repository unless the user explicitly asks to create a new label.

## Output Format

Return results in this structure:

1. `Action run`: exact pwm command executed.
2. `Outcome`: what changed (branch, issue state, PR status).
3. `Notes`: warnings/skips/degraded behavior.

Next-command contract:

- After successful `pwm pr`, return PR URL and validation status; omit
  `Next step`.
- After successful `pwm ws` or `pwm ic`, include `Next step` only when the
  user explicitly asked for end-to-end workflow execution.
- On failure, include exactly one corrective command as `Next step`.

## Safety And Fallbacks

- Never expose Jira, GitHub, or OpenAI tokens.
- If Jira is unavailable, continue with git-only guidance, clearly state Jira
  actions were skipped, and provide the smallest corrective step.
- If command execution fails, include the failing command, likely cause, and
  smallest corrective step.

## References

- `REFERENCE.md`
