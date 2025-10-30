
# pwm Development Roadmap

----------------------------------------

## Current Features

- pwm init: Interactive project configuration generator with GitHub remote inference.
- pwm work-start: Create or switch Git branches using a configurable pattern, transition Jira issues, and add comments.
- pwm self-check: Validates Git, Jira, and GitHub connectivity with helpful hints.

----------------------------------------

## Upcoming (Short-Term)

- pwm gh pr open: create GitHub pull requests with a template body and default reviewers/labels.
- pwm work done: transition Jira issues to review or done, and optionally open a PR.
- Improved config validation and clearer CLI feedback when configs are incomplete.
- Color-coded CLI output and improved error grouping in self-check.

----------------------------------------

## Medium-Term Goals

- Caching layer for Jira and GitHub data.
- Configurable commit templates with Jira keys.
- Changelog generation from merged PRs.
- Textual-based dashboard for current branches and PRs.

----------------------------------------

## Long-Term Ideas

- Plugin system for other integrations (GitLab, Linear, Notion).
- Team-shared project configs.
- Optional tmux or vim orchestration.
- Time logging and reporting synced with Jira.

----------------------------------------

## Testing

- Maintain fast, isolated unit tests by mocking network and git subprocesses.
- Target coverage: at least 80 percent for core modules.
- Add integration tests later using recorded fixtures.
