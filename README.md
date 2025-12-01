
# pwm - Personal Workflow Manager

pwm is a Python-based command-line tool designed to streamline daily developer workflows by integrating with Jira, Git, and GitHub.

It automatically detects project context, helps create and manage branches tied to Jira issues, initializes project settings, and validates connectivity to essential tools.

----------------------------------------

## Features

- Project context resolution: auto-detects the current Git repo and loads merged global and project configs.
- Config initialization: `pwm init` scaffolds `.pwm.toml` with inferred defaults (for example, the GitHub repo).
- Work start automation: `pwm work-start <ISSUE>` creates or switches to a branch, optionally transitions the Jira issue to In Progress, and adds a Jira comment. Use `--new` to create a new Jira issue first.
- Pull request automation: `pwm pr` creates or opens pull requests with auto-generated title and description from commits and Jira context.
- Status updates: `pwm work-end` posts concise summaries to PR and Jira with recent changes, optionally requesting reviewers.
- Daily work summaries: `pwm daily-summary` generates comprehensive reports of PRs and Jira issues from the previous business day, with optional AI summaries and org-wide search.
- AI-powered PR descriptions (optional): OpenAI integration generates intelligent summaries for pull request descriptions. Use `--no-ai` to skip. Fully optional with graceful fallback when not configured.
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
| OpenAI | PWM_OPENAI_API_KEY or OPENAI_API_KEY (optional) |

**Git Configuration:**

```toml
[git]
# Configure which remote to use for operations (default: "origin")
default_remote = "origin"
```

The `default_remote` setting controls which Git remote pwm uses for:
- Determining the default branch when creating new branches
- Pushing branches to remote
- Inferring the GitHub repository

**Custom Field Defaults:**

If your Jira project requires custom fields (like "Responsible Team"), you can configure defaults in your config file. When you use `pwm work-start --new`, you'll be prompted to save these values as defaults for future issues.

```toml
[jira.issue_defaults]
issue_type = "Story"
labels = ["backend", "api"]

# Custom fields are saved automatically when you choose to save defaults
# Example: Custom field for "Responsible Team" (single-select)
[jira.issue_defaults.custom_fields.customfield_10370]
value = "Platform Team"

# Example: String custom field
[jira.issue_defaults.custom_fields.customfield_12345]
"Some default value"
```

You can also manually add custom field defaults to your config file. See `example.pwm.toml` for more configuration examples.

----------------------------------------

## Commands

### pwm context
Show resolved project context including repository root, GitHub repo, Jira project key, and configuration file paths with their sources.

### pwm init
Initialize a `.pwm.toml` for the current repository. Prompts for Jira project key, GitHub repo, and branch naming pattern. Defaults to the current GitHub remote if detected.

### pwm work-start [ISSUE] (alias: ws)
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
- Story points (optional, numeric)
- Any required custom fields returned by your Jira instance (e.g., "Responsible Team")

After creating the issue, you'll be asked if you want to save the issue type, labels, and custom fields as defaults for future issues. These defaults are saved to `.pwm.toml` and will be pre-filled the next time you create an issue.

Note: `--new` requires Jira to be configured. See Configuration section above.

**Work on existing issue:**
```
pwm work-start ABC-123
pwm work-start ABC-123 --no-transition --no-comment
```

**Jira integration:**
- Jira transitions (to "In Progress") and comments run only when Jira credentials are configured
- When Jira is not configured, these operations are skipped and reported as such
- Branch creation always works, regardless of Jira configuration

### pwm pr
Open or create a pull request for the current branch.

If you're on a branch with a Jira issue key:
- If a PR already exists, opens it in your browser
- If no PR exists, creates one with:
  - Auto-generated title (from Jira issue if available, otherwise from first commit)
  - AI-generated summary (when OpenAI configured)
  - Description including Jira link, issue description, and commit summary
  - Automatic push to remote if needed

**Options:**
- `--no-ai`: Skip AI-generated summary even when OpenAI is configured

**AI integration:**
- When OpenAI is configured, automatically generates intelligent PR summaries
- Falls back to commit list if OpenAI not configured or API call fails
- Use `--no-ai` flag to skip AI generation

**Jira integration:**
- Jira links and issue descriptions appear in PR description only when Jira is configured and API calls succeed
- If Jira is not configured, PR is still created with commit-based title and description

```
pwm pr
pwm pr --no-ai
```

### pwm work-end (alias: we)
Post a status update to both the PR and Jira issue with a summary of recent changes.

Analyzes commits and generates a concise 1-2 sentence summary, then posts it to:
- GitHub PR as a comment (always, when GitHub is configured)
- Jira issue with clickable PR link (only when Jira is configured)

Works with both open and closed/merged PRs.

**Jira integration:**
- Jira comments are skipped when Jira is not configured
- GitHub PR comments work independently of Jira configuration

**Options:**
- `--message "text"` or `-m "text"`: Use custom message instead of auto-generated summary
- `--no-comment`: Skip all comments
- `--no-pr-comment`: Skip PR comment only
- `--no-jira-comment`: Skip Jira comment only
- `--request-review`: Request reviewers from config

**Examples:**
```
pwm work-end                                    # Auto-generate summary
pwm work-end -m "Ready for review"             # Custom message
pwm work-end --request-review                   # Request reviewers
pwm work-end --no-jira-comment                  # Only comment on PR
```

**Configure reviewers in `.pwm.toml`:**
```toml
[github.pr_defaults]
reviewers = ["teammate1", "teammate2"]
team_reviewers = ["platform-team"]
```

### pwm self-check
Validate connections to Git, Jira, and GitHub and show remediation hints.

### pwm daily-summary (alias: ds)
Generate a comprehensive summary of work from the previous business day to now.

Automatically calculates the previous business day:
- **Monday**: Shows Friday through Monday
- **Tuesday-Friday**: Shows previous day through current time
- **Saturday/Sunday**: Shows Friday through current time

Tracks:
- **GitHub PRs**: Opened, merged, and closed (without merging)
- **Jira Issues**: Created and updated

**Scope options:**
- Search across all repos in a GitHub organization (not just current repo)
- Search across multiple Jira projects (not just current project)

**Options:**
- `--since "2025-01-10 09:00"`: Custom start time (YYYY-MM-DD HH:MM)
- `--no-ai`: Skip AI-generated executive summary
- `--format [text|markdown]`: Output format (default: markdown)
- `--output report.md` or `-o report.md`: Save to file
- `--links`: Show clickable URLs for PRs and Jira issues

**Examples:**
```bash
pwm daily-summary                              # Auto-detect previous business day
pwm ds                                         # Short alias
pwm ds --since "2025-01-10 09:00"              # Custom date range
pwm ds --no-ai                                 # Skip AI summary
pwm ds --links --output daily.md               # With links, save to file
pwm ds --format text                           # Plain text format
```

**Configuration (optional):**
```toml
[daily_summary]
# Search across organization/multiple projects
github_org = "MyOrg"                    # Search all repos in org
jira_projects = ["PROJ1", "PROJ2"]      # Search multiple projects

# Filter options (default: only your work)
include_own_prs_only = true
include_own_issues_only = true

# Display options
default_format = "markdown"             # or "text"
```

**AI integration:**
- When OpenAI is configured, generates a 2-3 sentence executive summary
- Summarizes key themes and accomplishments from the work period
- Use `--no-ai` to skip AI generation

**Output example:**
```markdown
# Daily Work Summary
**Period:** Friday, Jan 10 2025 00:00 - Monday, Jan 13 2025 12:00

## Pull Requests

### Opened (4)
- #314 [PROJ-123] Add new authentication feature
- #315 [PROJ-124] Fix bug in payment processing

### Merged (6)
- #310 [PROJ-120] Update dependencies
- #311 [PROJ-121] Refactor database queries

### Closed (0)

## Jira Issues

### Created (3)
- PROJ-125: Implement user notifications
- PROJ-126: Fix edge case in search

### Updated (5)
- PROJ-100: Add API documentation → Done
- PROJ-101: Review security audit → In Progress
```

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
