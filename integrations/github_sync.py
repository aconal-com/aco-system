"""
GitHub Sync - Sync database with GitHub Issues.

This module handles:
- Creating issues from stories
- Updating labels based on story status
- Adding comments to issues
- Syncing state between DB and GitHub
"""
import logging
import httpx
from typing import Dict, List, Optional
from datetime import datetime

from config.settings import get_settings
from core.database import Story, StoryComment, Task

logger = logging.getLogger(__name__)


class GitHubSync:
    """Sync database stories with GitHub issues."""

    # Workflow labels mapping
    STATUS_LABELS = {
        "pm-review": "pm-review",
        "ready-planner": "ready-planner",
        "ready-architect": "ready-architect",
        "approved": "approved",
        "dev": "dev",
        "qa": "qa",
        "human-review": "human-review",
        "done": "done",
    }

    def __init__(self):
        self.settings = get_settings()
        self.base_url = f"https://api.github.com/repos/{self.settings.GITHUB_OWNER}/{self.settings.GITHUB_REPO}"
        self.headers = {
            "Authorization": f"Bearer {self.settings.GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }
        self.session = httpx.Client(timeout=30.0)

    def create_issue(self, story: Story, tasks: List[Task] = None) -> int:
        """Create a GitHub issue from a story. Returns issue number."""
        from core.database import get_session

        # Fetch tasks if not provided
        if tasks is None:
            db = get_session()
            tasks = db.query(Task).filter(Task.story_id == story.id).all()
            db.close()

        issue_body = self._format_issue_body(story, tasks)

        payload = {
            "title": f"Story #{story.id}: {story.title}",
            "body": issue_body,
            "labels": [self.STATUS_LABELS.get(story.status.value, "pm-review")],
        }

        response = self.session.post(
            f"{self.base_url}/issues",
            headers=self.headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        issue_number = data["number"]
        return issue_number

    def create_task_issue(self, story: Story, task: Task) -> int:
        """Create a GitHub issue for a specific task linked to a story."""
        parent_issue_number = story.context_json.get("github_issue_number")

        issue_body = f"""## Task: {task.title}

**Part of Story:** #{parent_issue_number}
**Status:** `{task.status.value}`
**Estimated Hours:** {task.estimate_hours or 0}

### Description

{task.description}

### Technical Notes

{task.output_json.get('technical_notes', '')}

### Acceptance Criteria

{task.output_json.get('acceptance', '')}
"""
        payload = {
            "title": f"Task #{task.id}: {task.title}",
            "body": issue_body,
            "labels": ["task", "dev"]
        }

        response = self.session.post(
            f"{self.base_url}/issues",
            headers=self.headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        return data["number"]

    def update_issue_labels(self, story: Story, issue_number: int):
        """Update GitHub issue labels based on story status."""
        label = self.STATUS_LABELS.get(story.status.value, "pm-review")

        payload = {"labels": [label]}

        response = self.session.patch(
            f"{self.base_url}/issues/{issue_number}",
            headers=self.headers,
            json=payload,
        )
        response.raise_for_status()

    def add_comment(self, story_id: int, issue_number: int, comment: StoryComment):
        """Add a comment to GitHub issue."""
        formatted_comment = self._format_comment(comment)

        payload = {"body": formatted_comment}

        response = self.session.post(
            f"{self.base_url}/issues/{issue_number}/comments",
            headers=self.headers,
            json=payload,
        )
        response.raise_for_status()

    def close_issue(self, issue_number: int):
        """Close a GitHub issue (when story is done)."""
        payload = {"state": "closed"}

        response = self.session.patch(
            f"{self.base_url}/issues/{issue_number}",
            headers=self.headers,
            json=payload,
        )
        response.raise_for_status()

    def _format_issue_body(self, story: Story, tasks: List[Task] = None) -> str:
        """Format story content as GitHub issue body."""
        body = f"""## Story: {story.title}

**Status:** `{story.status.value}`
**Priority:** {story.priority}
**Assigned Agent:** `{story.assigned_agent or 'None'}`

### Description

{story.description}

### Acceptance Criteria

"""
        for i, criteria in enumerate(story.acceptance_criteria or [], 1):
            body += f"{i}. {criteria}\n"

        body += "\n### Context\n\n"

        for key, value in (story.context_json or {}).items():
            if key not in ["pm_summary", "planner_summary", "architect_approval"]:
                body += f"**{key}:** {value}\n"

        body += "\n### Tasks\n\n"

        if tasks:
            for task in tasks:
                status_emoji = "✅" if task.status.value == "done" else "⏳"
                body += f"{status_emoji} **{task.title}** ({task.estimate_hours or 0}h)\n"
                body += f"   {task.description}\n\n"
        else:
            body += "No tasks created yet.\n"

        return body

    def _format_comment(self, comment: StoryComment) -> str:
        """Format a comment for GitHub."""
        icons = {
            "question": "❓",
            "answer": "💬",
            "decision": "🔶",
            "note": "📝",
            "escalation": "⚠️",
        }

        icon = icons.get(comment.comment_type, "💬")

        return f"""{icon} **{comment.comment_type.upper()}** by {comment.author}

{comment.content}
"""

    def create_task_issues(self, story: Story, tasks: List[Task]) -> List[int]:
        """Create separate GitHub issues for each task. Returns list of issue numbers."""
        from core.database import get_session

        story_issue = story.context_json.get("github_issue_number", f"Story #{story.id}")
        db_session = get_session()

        task_issue_numbers = []
        try:
            for task in tasks:
                priority_label = "priority-high" if story.priority == "high" else "priority-low"
                body = f"""**Parent Story:** #{story_issue}

## Task: {task.title}

**Story ID:** #{story.id}
**Task ID:** #{task.id}
**Estimate:** {task.estimate_hours or 0} hours
**Status:** `{task.status.value}`

### Description

{task.description}

### Technical Notes

{task.output_json.get('technical_notes', 'N/A') if task.output_json else 'N/A'}

### Dependencies

{', '.join(f'#{d}' for d in (task.dependencies or [])) or 'None'}

---
_Generated by ACO System_"""

                payload = {
                    "title": f"Task #{task.id}: {task.title}",
                    "body": body,
                    "labels": ["task", priority_label],
                }

                try:
                    response = self.session.post(
                        f"{self.base_url}/issues",
                        headers=self.headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    issue_number = data["number"]
                    task_issue_numbers.append(issue_number)

                    # Store issue number in task's output_json
                    current_output = task.output_json or {}
                    current_output["github_issue_number"] = issue_number
                    task.output_json = current_output
                    db_session.commit()
                    logger.info(f"Created GitHub issue #{issue_number} for Task #{task.id}")
                except Exception as e:
                    logger.error(f"Failed to create issue for Task #{task.id}: {e}")
        finally:
            db_session.close()

        return task_issue_numbers

    def close(self):
        """Close HTTP session."""
        self.session.close()


# Global sync instance
_github_sync: Optional[GitHubSync] = None


def get_github_sync() -> GitHubSync:
    """Get or create global GitHub sync instance."""
    global _github_sync
    if _github_sync is None:
        _github_sync = GitHubSync()
    return _github_sync
