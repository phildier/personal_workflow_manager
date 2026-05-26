# PWM Workflow Reference

## Preconditions

- `pwm --help` succeeds.
- Repository is a git repo with configured `.pwm.toml`.
- Optional integrations configured through env vars:
  - Jira: `PWM_JIRA_TOKEN`, `PWM_JIRA_EMAIL`, `PWM_JIRA_BASE_URL`
  - GitHub: `GITHUB_TOKEN` or `PWM_GITHUB_TOKEN`
  - OpenAI: `PWM_OPENAI_API_KEY` or `OPENAI_API_KEY`

## Non-Interactive Work Start

- Minimum new issue command:
  - `pwm ws --new --non-interactive --summary "Implement feature X"`
- Full new issue command:
  - `pwm ws --new --non-interactive --summary "Implement feature X" --description "Details" --issue-type Task --labels backend,api --story-points 3 --custom-field customfield_10370='{"value":"Platform Team"}' --save-defaults`

## Non-Interactive PR

- Safe automation mode:
  - `pwm pr --non-interactive --no-open-browser`
- Force creation when branch has no commits ahead of base:
  - `pwm pr --non-interactive --create-anyway --no-open-browser`
- Optional title/body override:
  - `pwm pr --title "[ABC-123] Manual title" --body "Manual summary"`
- Apply labels to PR (repeatable):
  - `pwm pr --non-interactive --no-open-browser --label bug --label ai-assisted`
- Disable AI-generated PR metadata when needed:
  - `pwm pr --no-ai --non-interactive --no-open-browser`

Label behavior:
- Labels are only added when `--label` is provided.
- Labels are applied to both existing PRs and newly created PRs.
- Duplicate/blank label values are normalized before being sent.

## Label Decision Rules

- Use `--label ai-assisted` when code additions are 50% or more of the PR's
  total code changes.
- Use `--label bug` when "bug" appears in the user's prompt.
- Do not apply other labels without first asking the user.
- Do not create new labels automatically; only use labels already available in
  the repository unless the user explicitly requests creating a new label.

## Troubleshooting

- `pwm: command not found`
  - Install package in current environment (`pip install -e .`) or use pipx.
- Jira auth/config errors
  - Re-check Jira env vars and base URL format.
- No remote branch or PR creation failure
  - Ensure current branch has an upstream and push if needed.
- Prompt appears in non-interactive flow
  - Add `--non-interactive` plus `--save-defaults` or `--no-save-defaults`.

## Expected Report Template

```text
Action run: pwm ws --new --non-interactive --summary "Implement feature X"
Outcome: Created issue ABC-123 and switched to branch ABC-123-implement-feature-x.
Notes: Jira transition/comment skipped by flags.
Next step: pwm pr --non-interactive --no-open-browser
```

## Command Logging

- `pwm ws` and `pwm pr` events are logged to `~/.config/pwm/log.jsonl`.
- Logs include timestamp, command, normalized args, and details such as repo,
  branch, issue key, and PR URL when available.
