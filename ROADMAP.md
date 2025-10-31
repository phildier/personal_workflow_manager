
# pwm Development Roadmap

----------------------------------------

## Current Features

- pwm init: Interactive project configuration generator with GitHub remote inference.
- pwm work-start: Create or switch Git branches using a configurable pattern, transition Jira issues, and add comments. Supports creating new Jira issues interactively with --new flag.
- pwm pr: Open or create pull requests with auto-generated title and description from commits and Jira. Opens existing PRs in browser if already created.
- pwm work-end: Post status updates to PR and Jira with auto-generated summaries, optionally request reviewers from config. Features smart commit tracking to show only new commits since last update.
- pwm self-check: Validates Git, Jira, and GitHub connectivity with helpful hints.
- pwm prompt: Shell prompt integration showing current Jira issue with optional status, colors, and emoji.

----------------------------------------

## Upcoming (Short-Term)

- Enhanced PR creation: Add support for default labels from config.
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
