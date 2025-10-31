# AGENTS.md

## Project Overview

The Personal Workflow Manager (pwm) is a Python-based command-line application that integrates with Jira, Git, and GitHub to automate and streamline daily developer workflows.

It provides commands for:
- Project setup (`pwm init`)
- Context-aware branch creation and Jira issue tracking (`pwm work-start`)
- Pull request creation and management (`pwm pr`)
- System self-checks for environment validation (`pwm self-check`)

The goal of pwm is to automate common engineering tasks while maintaining a modular, extensible design.

----------------------------------------

## Development Environment

**Tooling:**
- Python 3.11 or newer
- pip or pipx for dependency management
- pytest for testing
- git for CLI-level integrations

**Installation:**
1. Clone the repository
   ```bash
   git clone <repo-url>
   cd pwm
   ```
2. Install dependencies
   ```bash
   pip install -e .
   ```
   or
   ```bash
   pipx install -e .
   ```
3. Verify installation
   ```bash
   pwm --help
   ```

----------------------------------------

## Common Commands

**Show project context**
```bash
pwm context
```

**Initialize a project**
```bash
pwm init
```

**Start work on a Jira issue**
```bash
# Create a new issue interactively
pwm work-start --new

# Work on existing issue
pwm work-start ABC-123
pwm work-start ABC-123 --no-transition --no-comment
```

**Open or create a pull request**
```bash
pwm pr
```

**Run diagnostics**
```bash
pwm self-check
```

**Show prompt info (for shell integration)**
```bash
pwm prompt
pwm prompt --with-status --color
pwm prompt --format emoji
```

**Run tests**
```bash
pytest
pytest --cov=pwm --cov-report=term-missing
```

----------------------------------------

## Coding Conventions

- Language: Python 3.11+
- Formatting: Follow PEP8; prefer Black-compatible formatting.
- File Naming: Use snake_case for modules and files.
- Constants: Use ALL_CAPS for constant variables.
- Error Handling: Wrap API and subprocess calls in try/except blocks.
- Type Hints: Required for all functions and return values.
- Docstrings: Use PEP257 triple-quoted strings.
- Imports: Group as standard library, third-party, then local imports.
- Line Length: Limit to 85 characters.

----------------------------------------

## Architectural Guidance

The codebase follows a domain-based architecture where each directory represents a functional domain:

- **CLI Layer (pwm/cli.py)**
  Handles argument parsing (Typer) and delegates to domain command modules.

- **Context Domain (pwm/context/)**
  - `resolver.py`: Resolves repository root, reads configs, merges env vars
  - `command.py`: Implements the `pwm context` command

- **Setup Domain (pwm/setup/)**
  - `init.py`: Implements the `pwm init` command for project initialization

- **Work Domain (pwm/work/)**
  - `start.py`: Implements the `pwm work-start` command
  - `create_issue.py`: Handles interactive Jira issue creation

- **Check Domain (pwm/check/)**
  - `self_check.py`: Implements the `pwm self-check` command for diagnostics

- **Prompt Domain (pwm/prompt/)**
  - `command.py`: Implements the `pwm prompt` command for shell integration

- **PR Domain (pwm/pr/)**
  - `open.py`: Implements the `pwm pr` command for pull request creation

- **Config (pwm/config/)**
  Defines configuration schema with Pydantic models.

- **VCS (pwm/vcs/)**
  Provides subprocess-based Git helpers for branch operations and remote detection.

- **Jira (pwm/jira/)**
  REST API client for issue management, transitions, and comments.

- **GitHub (pwm/github/)**
  REST API client for token validation and PR creation/management.

----------------------------------------

## Security Best Practices

- **Tokens and Credentials**
  - Jira: PWM_JIRA_TOKEN, PWM_JIRA_EMAIL, PWM_JIRA_BASE_URL
  - GitHub: GITHUB_TOKEN or PWM_GITHUB_TOKEN
  - Never commit credentials or embed them in source code.

- **Network Handling**
  - Validate HTTP responses and handle all exceptions.

- **Logging**
  - Redact secrets and emails in all output.

----------------------------------------

## Other Notes

- Keep README.md, ROADMAP.md, and AGENTS.md synchronized with code updates.
- Follow Conventional Commits specification for commit messages.
- Test code should use mocks for Git subprocesses and network operations.
- Only use dependencies declared in pyproject.toml.
- Agents can safely modify CLI commands, config loading, and test coverage expansion as long as architecture boundaries are respected.
