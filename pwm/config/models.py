
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class JiraIssueDefaults(BaseModel):
    issue_type: str = "Story"
    labels: list[str] = Field(default_factory=list)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)  # e.g., {"customfield_10370": {"value": "Team A"}}

class JiraConfig(BaseModel):
    base_url: Optional[str] = None
    email: Optional[str] = None
    token: Optional[str] = None
    project_key: Optional[str] = None
    issue_defaults: JiraIssueDefaults = Field(default_factory=JiraIssueDefaults)

class GithubPRDefaults(BaseModel):
    reviewers: list[str] = Field(default_factory=list)  # List of GitHub usernames
    team_reviewers: list[str] = Field(default_factory=list)  # List of team slugs

class GithubConfig(BaseModel):
    base_url: Optional[str] = None
    token: Optional[str] = None
    default_org: Optional[str] = None
    repo: Optional[str] = None
    pr_defaults: GithubPRDefaults = Field(default_factory=GithubPRDefaults)

class GitConfig(BaseModel):
    default_remote: str = "origin"

class BranchConfig(BaseModel):
    pattern: str = "{issue_key}-{slug}"

class OpenAIConfig(BaseModel):
    api_key: Optional[str] = None
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    max_tokens: int = 500
    temperature: float = 0.7

class UIConfig(BaseModel):
    editor: Optional[str] = None

class DailySummaryConfig(BaseModel):
    """Configuration for daily summary feature."""

    # Scope configuration
    github_org: Optional[str] = None  # If set, search all repos in org instead of current repo
    jira_projects: Optional[list[str]] = None  # If set, search these projects instead of current project

    # Filter options
    include_own_commits_only: bool = True
    include_own_prs_only: bool = True
    include_own_issues_only: bool = True

    # Display options
    default_format: str = "markdown"  # "text" or "markdown"
    show_commit_details: bool = True
    group_commits_by_branch: bool = True
    max_commits_per_branch: int = 10

    # Business day configuration
    work_start_hour: int = 0
    work_end_hour: int = 23

class PWMConfig(BaseModel):
    jira: JiraConfig = Field(default_factory=JiraConfig)
    github: GithubConfig = Field(default_factory=GithubConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    branch: BranchConfig = Field(default_factory=BranchConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    daily_summary: DailySummaryConfig = Field(default_factory=DailySummaryConfig)

    def as_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)
