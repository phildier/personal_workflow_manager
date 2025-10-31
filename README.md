
# pwm - Personal Workflow Manager

pwm is a Python-based command-line tool designed to streamline daily developer workflows by integrating with Jira, Git, and GitHub.

It automatically detects project context, helps create and manage branches tied to Jira issues, initializes project settings, and validates connectivity to essential tools.

----------------------------------------

## Features

- Project context resolution: auto-detects the current Git repo and loads merged global and project configs.
- Config initialization: `pwm init` scaffolds `.pwm.toml` with inferred defaults (for example, the GitHub repo).
- Work start automation: `pwm work-start <ISSUE>` creates or switches to a branch, optionally transitions the Jira issue to In Progress, and adds a Jira comment. Use `--new` to create a new Jira issue first.
- Pull request automation: `pwm pr` creates or opens pull requests with auto-generated title and description from commits and Jira context.
- Self-check diagnostics: `pwm self-check` validates Git repo status, Jira API credentials, and GitHub API connectivity with helpful hints for missing environment variables.

----------------------------------------

## Installation

```bash
pip install -e .
# or for isolation
pipx install -e .
```

Requires Python 3.11 or newer.

----------------------------------------

## Configuration

Global config: `~/.config/pwm/config.toml`
Project config: `<repo>/.pwm.toml`

Environment variable overrides (recommended for tokens):

| Service | Variables |
|----------|------------|
| Jira | PWM_JIRA_TOKEN, PWM_JIRA_EMAIL, PWM_JIRA_BASE_URL |
| GitHub | GITHUB_TOKEN or PWM_GITHUB_TOKEN |

**Custom Field Defaults:**

If your Jira project requires custom fields (like "Responsible Team"), you can configure defaults in your config file:

```toml
[jira.issue_defaults]
issue_type = "Story"
labels = ["backend", "api"]

# Custom field for "Responsible Team" (single-select)
[jira.issue_defaults.custom_fields.customfield_10370]
value = "Platform Team"
```

See `example.pwm.toml` for more configuration examples.

----------------------------------------

## Commands

### pwm context
Show resolved project context including repository root, GitHub repo, Jira project key, and configuration file paths with their sources.

### pwm init
Initialize a `.pwm.toml` for the current repository. Prompts for Jira project key, GitHub repo, and branch naming pattern. Defaults to the current GitHub remote if detected.

### pwm work-start [ISSUE]
Start work on a Jira issue: create or switch branches and update Jira.

**Create a new issue:**
```
pwm work-start --new
```
Interactively creates a new Jira issue, then creates a branch and starts work. Prompts for:
- Summary (required)
- Description (optional)
- Issue type (Story, Task, Bug, etc.)
- Labels (comma-separated, optional)

Issue type and labels are saved as defaults for next time.

**Work on existing issue:**
```
pwm work-start ABC-123
pwm work-start ABC-123 --no-transition --no-comment
```

### pwm pr
Open or create a pull request for the current branch.

If you're on a branch with a Jira issue key:
- If a PR already exists, opens it in your browser
- If no PR exists, creates one with:
  - Auto-generated title from Jira issue
  - Description including Jira link, issue description, and commit summary
  - Automatic push to remote if needed

```
pwm pr
```

### pwm self-check
Validate connections to Git, Jira, and GitHub and show remediation hints.

### pwm prompt
Generate shell prompt information showing current Jira issue from branch name. Use this in your PS1/PROMPT for at-a-glance work context.

**Options:**
- `--with-status`: Fetch and display current Jira status (cached for 5 minutes)
- `--format [default|minimal|emoji]`: Choose output style
  - `default`: `[ABC-123]` or `[ABC-123: In Progress]`
  - `minimal`: `ABC-123` or `ABC-123: In Progress`
  - `emoji`: `🔹 ABC-123` or `🎯 ABC-123` (status-based emoji)
- `--color`: Use ANSI color codes (status-based colors)

**Shell integration:**
```bash
# Bash (~/.bashrc)
export PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w$(pwm prompt 2>/dev/null)\$ '

# With color and status (slower due to API call)
export PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w$(pwm prompt --with-status --color 2>/dev/null)\$ '

# Zsh (~/.zshrc)
PROMPT='%n@%h:%~$(pwm prompt 2>/dev/null)%# '
```

----------------------------------------

## Testing

Run unit tests:
```
pytest
```

Optional coverage:
```
pytest --cov=pwm --cov-report=term-missing
```

----------------------------------------

## License

MIT License (c) 2025
