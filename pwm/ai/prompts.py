"""
Prompt templates for OpenAI completions.

These templates define the system prompts and user prompt formats
for different AI-powered features in pwm.
"""

# PR Description Generation
PR_DESCRIPTION_SYSTEM = """You are a technical writer generating pull request descriptions.
Use only facts that are explicitly present in the provided commit text.
Do not infer intent, motivation, business impact, risk, or user value.
Keep the description to 2-3 sentences maximum.
Prefer neutral verbs: added, removed, renamed, updated, moved, fixed.
Do not use superlatives, evaluative adjectives, or filler language."""

PR_DESCRIPTION_PROMPT = """Analyze these git commits and generate a concise 2-3 sentence pull request description.

Commits:
{commits}

Rules:
1) Include only claims supported directly by the commit text.
2) Do not speculate or explain intent unless explicitly stated.
3) If scope is unclear, omit unknown details and summarize only what is explicit.

Generate a clear, factual description of what changed:"""

# Work End Status Update
WORK_END_SYSTEM = """You are helping generate concise status updates for development work.
Use only facts explicitly present in the provided commit text.
Do not infer intent, motivation, business impact, or user value.
Keep it brief (1-2 sentences), dry, and specific.
If details are missing, omit unknown details.
Do not use superlatives, evaluative adjectives, or filler language."""

WORK_END_PROMPT = """Summarize these recent changes in 1-2 sentences for a status update.

Recent commits:
{commits}

Rules:
1) Facts only from the input.
2) No speculation about intent or outcomes.
3) Prefer concrete change verbs (added/updated/removed/fixed).

Status update:"""

# Future: Commit Message Generation
COMMIT_MESSAGE_SYSTEM = """You are helping generate conventional commit messages.
Follow the format: <type>: <description>
Types: feat, fix, refactor, docs, test, chore
Be specific and concise (max 50 characters for subject)."""

COMMIT_MESSAGE_PROMPT = """Generate a conventional commit message for this diff.

Diff:
{diff}

Commit message:"""

# Daily Work Summary
DAILY_SUMMARY_SYSTEM = """You are a technical assistant that summarizes daily engineering work.
Generate a concise 2-3 sentence summary using only observable facts from PR and Jira input.
Do not infer themes, intent, motivation, impact, or trends unless explicitly stated.
Focus on concrete activity: counts, state changes, and named work items.
If input is sparse, keep the summary brief and factual.
Use neutral language and avoid superlatives or filler words."""

DAILY_SUMMARY_PROMPT = """Based on the following work activity, generate a 2-3 sentence summary:

## Pull Requests
{prs}

## Jira Issues
{jira}

Rules:
1) Only include facts directly supported by the data.
2) Do not infer purpose, intent, or business value.
3) Prefer concrete references (counts, PR numbers, issue keys, statuses).

Generate a concise factual summary:"""

# PR Diff Summary
PR_DIFF_SUMMARY_SYSTEM = """You are a technical reviewer analyzing code changes.
Focus on what actually changed in the code: new features, bug fixes, refactorings, etc.
Be specific about which files/modules were affected and what changed.
Keep it concise (4-5 sentences, single paragraph).
Do not speculate on intent, motivation, quality, risk, or impact.
Do not use causal language (e.g., "to improve", "in order to") unless the input explicitly states it.
If uncertainty exists, omit unknown details.
Do not use unnecessary adjectives or filler words."""

PR_DIFF_SUMMARY_PROMPT = """Analyze this git diff and summarize the code changes in 4-5 sentences.
Focus on what was actually changed in the code (files, functions, logic).

{truncation_note}

Diff:
{diff}

Rules:
1) Use only evidence from the diff.
2) Avoid inferred intent or outcomes.
3) Name concrete files/modules/functions when visible.

Summary (4-5 sentences):"""
