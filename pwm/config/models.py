
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

class UIConfig(BaseModel):
    editor: Optional[str] = None

class PWMConfig(BaseModel):
    jira: JiraConfig = Field(default_factory=JiraConfig)
    github: GithubConfig = Field(default_factory=GithubConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    branch: BranchConfig = Field(default_factory=BranchConfig)
    ui: UIConfig = Field(default_factory=UIConfig)

    def as_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)
