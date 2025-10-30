# pwm - Personal Workflow Manager

pwm is a Python-based command-line tool designed to streamline daily developer workflows by integrating with Jira, Git, and GitHub.

It automatically detects project context, helps create and manage branches tied to Jira issues, initializes project settings, and validates connectivity to essential tools.

----------------------------------------

## Features

- Project context resolution: auto-detects the current Git repo and loads merged global and project configs.
- Config initialization: `pwm init` scaffolds `.pwm.toml` with inferred defaults (for example, the GitHub repo).
- Work start automation: `pwm work-start <ISSUE>` creates or switches to a branch, optionally transitions the Jira issue to In Progress, and adds a Jira comment.
- Self-check diagnostics: `pwm self-check` validates Git repo status, Jira API credentials, and GitHub API connectivity with helpful hints for missing environment variables.

----------------------------------------

## Installation

```bash
pip install -e .
# or for isolation
pipx install -e .
```

Requires Python 3.10 or newer.

----------------------------------------

## Configuration

Global config: `~/.config/pwm/config.toml`  
Project config: `<repo>/.pwm.toml`  

Example global config:

```toml
[jira]
base_url = "https://yourcompany.atlassian.net"
email = "you@company.com"

[github]
default_org = "your-org"

[git]
default_remote = "origin"

[branch]
pattern = "feature/{issue_key}-{slug}"
```

Environment variable overrides (recommended for tokens):

| Service | Variables |
|----------|------------|
| Jira | PWM_JIRA_TOKEN, PWM_JIRA_EMAIL, PWM_JIRA_BASE_URL |
| GitHub | GITHUB_TOKEN or PWM_GITHUB_TOKEN |

----------------------------------------

## Commands

### pwm init
Initialize a `.pwm.toml` for the current repository.

```bash
pwm init
```

Prompts for Jira project key, GitHub repo, and branch naming pattern.  
Defaults to the current GitHub remote if detected.

----------------------------------------

### pwm work-start <ISSUE>
Start work on a Jira issue: create or switch branches and update Jira.

```bash
pwm work-start ABC-123
# Optional flags
pwm work-start ABC-123 --no-transition --no-comment
```

Outputs a summary of created branches and Jira updates.

----------------------------------------

### pwm self-check
Validate connections to Git, Jira, and GitHub.

```bash
pwm self-check
```

Displays a diagnostic table with status and configuration hints.

----------------------------------------

## Project Structure

```
pwm/
  cli.py               # Typer CLI entrypoint
  context/             # Context resolver (repo root, configs)
  config/              # Pydantic models and loader
  commands/            # init command
  vcs/                 # Git CLI helpers
  jira/                # Jira API client
  github/              # GitHub API client
  work/                # Work management (for example, work-start)
  check/               # Self-check diagnostics
tests/
pyproject.toml
```

----------------------------------------

## License

MIT License (c) 2025
