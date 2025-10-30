# pwm Development Roadmap

This roadmap outlines the evolution of the Personal Workflow Manager (pwm) CLI tool.

----------------------------------------

## Current Features

- `pwm init`: Interactive project configuration generator.
- `pwm work-start`: Create or switch Git branches, transition Jira issues, and add comments.
- `pwm self-check`: Validates Git, Jira, and GitHub connectivity with helpful hints.

----------------------------------------

## Upcoming (Short-Term)

### GitHub PR Automation
- Command: `pwm gh pr open`
- Automatically create a pull request for the current branch.
- Use a configurable Jinja2 template for PR body.
- Apply labels, reviewers, and link Jira issue.

### pwm work done
- Transition Jira issue to "In Review" or "Done".
- Push branch and optionally open a PR.

### Improved Config Handling
- Add schema validation and clearer CLI feedback when configs are incomplete.

### Output Enhancements
- Color-coded CLI results (for example, green for success, red for failure).
- Better error grouping in self-check output.

----------------------------------------

## Medium-Term Goals

- Caching layer for Jira and GitHub data to speed up repeated operations.
- Configurable commit templates that include Jira issue keys automatically.
- Changelog generation from merged PRs.
- Interactive dashboard (TUI) for current branches, PRs, and assigned Jira issues using rich or textual.

----------------------------------------

## Long-Term Ideas

- Plugin system for adding integrations (GitLab, Linear, Notion, etc.).
- Team-shared project configs stored in repos.
- Optional tmux or vim orchestration layer for full-session setup.
- Time logging and reporting features (sync with Jira worklogs).

----------------------------------------

## Development Notes

- The architecture is designed for incremental growth: each domain (Git, Jira, GitHub, etc.) is modular.
- Every CLI command is thin and delegates logic to a dedicated module.
- Extensibility is a key goal: prefer clean interfaces over large monolithic functions.

----------------------------------------

## Contributing

Planned to support simple contribution workflow:

```bash
git clone <repo>
pip install -e .[dev]
pytest
```
