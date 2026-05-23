"""
GitHub Client - Wrapper for GitHub API operations.
"""
from typing import Optional, List, Dict, Any
from github import Github, GithubException
from github.Repository import Repository
from github.Branch import Branch

from config.settings import get_settings


class GitHubClient:
    """GitHub API client for repo operations."""
    
    def __init__(self, token: str, owner: str, repo: str):
        self.token = token
        self.owner = owner
        self.repo_name = repo
        self.gh = Github(token)
        self.repo: Optional[Repository] = None
        
    def connect(self):
        """Connect to the repository."""
        try:
            self.repo = self.gh.get_repo(f"{self.owner}/{self.repo_name}")
            return True
        except GithubException as e:
            raise RuntimeError(f"Failed to connect to repo: {e}")
    
    def create_branch(self, branch_name: str, base_branch: str = "main") -> Branch:
        """Create a new branch from base."""
        if not self.repo:
            self.connect()
        
        try:
            # Get the base branch
            base = self.repo.get_branch(base_branch)
            
            # Create new branch
            self.repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=base.commit.sha,
            )
            
            return self.repo.get_branch(branch_name)
            
        except GithubException as e:
            if "Reference already exists" in str(e):
                # Branch already exists, that's fine
                return self.repo.get_branch(branch_name)
            raise
    
    def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
    ) -> int:
        """Create a GitHub issue."""
        if not self.repo:
            self.connect()
        
        issue = self.repo.create_issue(
            title=title,
            body=body,
            labels=labels or [],
        )
        
        return issue.number
    
    def update_issue_labels(
        self,
        issue_number: int,
        labels: List[str],
    ):
        """Update labels on an issue."""
        if not self.repo:
            self.connect()
        
        issue = self.repo.get_issue(issue_number)
        issue.set_labels(labels)
    
    def add_issue_comment(self, issue_number: int, comment: str):
        """Add a comment to an issue."""
        if not self.repo:
            self.connect()
        
        issue = self.repo.get_issue(issue_number)
        issue.create_comment(comment)
    
    def create_file(
        self,
        path: str,
        content: str,
        message: str,
        branch: Optional[str] = None,
    ):
        """Create or update a file in the repo."""
        if not self.repo:
            self.connect()
        
        self.repo.create_file(
            path=path,
            message=message,
            content=content,
            branch=branch,
        )
    
    def create_pull_request(
        self,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> int:
        """Create a pull request."""
        if not self.repo:
            self.connect()
        
        pr = self.repo.create_pull(
            title=title,
            body=body,
            head=head,
            base=base,
        )
        
        return pr.number
    
    def get_issue(self, issue_number: int):
        """Get an issue by number."""
        if not self.repo:
            self.connect()
        
        return self.repo.get_issue(issue_number)
    
    def sync_story_to_issue(
        self,
        story_id: int,
        title: str,
        body: str,
        labels: List[str],
    ) -> int:
        """
        Sync a story to a GitHub issue.
        Creates if doesn't exist, updates if does.
        """
        # For now, just create a new issue
        # Later: Track issue numbers in database
        return self.create_issue(title, body, labels)


# Global client instance
_github_client: Optional[GitHubClient] = None


def get_github_client() -> GitHubClient:
    """Get or create the global GitHub client."""
    global _github_client
    if _github_client is None:
        settings = get_settings()
        _github_client = GitHubClient(
            token=settings.GITHUB_TOKEN,
            owner=settings.GITHUB_OWNER,
            repo=settings.GITHUB_REPO,
        )
        _github_client.connect()
    return _github_client
