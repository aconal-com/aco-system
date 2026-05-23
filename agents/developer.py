"""
Developer Agent (aco-dev)

Responsibilities:
- Pick up approved stories and implement tasks
- GENERATE ACTUAL CODE FILES (not just comments)
- Use appropriate tech stack:
  - Flutter/Dart for mobile tasks
  - Python/FastAPI for backend tasks
  - HTML/CSS/JS for web tasks
- Create proper file structure
- Commit code to Git
- Mark tasks as complete
- Move story to QA when all tasks done

Workflow:
1. Pick up story with status "approved"
2. For each task (respecting dependencies):
   - Identify task type (mobile, backend, web)
   - Generate code using LLM
   - Write files to project directory
   - Commit to Git
   - Mark task complete
3. When all tasks done → Mark story as "qa"
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from agents.base_agent import BaseAgent
from core.database import Story, Task, StoryStatus, TaskStatus
from integrations.llm_client import get_client
from integrations.github_client import get_github_client


class DeveloperAgent(BaseAgent):
    """Developer agent that generates and writes actual code files."""

    AGENT_NAME = "aco-dev"
    HANDLES_STATUSES = [StoryStatus.APPROVED]

    # Tech stack mapping
    TECH_STACKS = {
        'flutter': {'lang': 'dart', 'ext': '.dart'},
        'fastapi': {'lang': 'python', 'ext': '.py'},
        'react': {'lang': 'javascript', 'ext': '.js'},
        'html': {'lang': 'html', 'ext': '.html'},
    }

    def __init__(self):
        super().__init__()
        self.gh = get_github_client()

    def process_story(self, story: Story):
        """
        Implement all tasks for an approved story.
        """
        try:
            self.emit("picked_up", story, f"Starting development: {story.title}")
            self.logger.info(f"Developing Story #{story.id}: {story.title}")

            # Get tasks for this story
            tasks = (
                self.db.query(Task)
                .filter(Task.story_id == story.id)
                .order_by(Task.id.asc())
                .all()
            )

            # Filter to only TODO tasks
            todo_tasks = [t for t in tasks if t.status == TaskStatus.TODO]

            if not todo_tasks:
                self.logger.info(f"All tasks already complete for Story #{story.id}")
                self.update_story_status(story, StoryStatus.QA)
                return

            # Create project directory structure
            project_dir = Path(f"projects/{story.id}")
            project_dir.mkdir(parents=True, exist_ok=True)

            # Implement tasks in dependency order
            for task in self._get_tasks_in_order(todo_tasks):
                self._implement_task(task, story, project_dir)

            # All tasks complete
            self._complete_story(story, todo_tasks)

        except Exception as e:
            self.logger.error(f"Error in development: {e}", exc_info=True)
            self.release_story(story)
            raise

    def _get_tasks_in_order(self, tasks: List[Task]) -> List[Task]:
        """Sort tasks by dependencies (topological sort)."""
        implemented = set()
        ordered = []

        while len(ordered) < len(tasks):
            for task in tasks:
                if task.id in implemented:
                    continue
                # Check if dependencies are met
                deps_met = all(
                    dep_id in implemented
                    for dep_id in (task.dependencies or [])
                )
                if deps_met:
                    ordered.append(task)
                    implemented.add(task.id)
                    break

        return ordered

    def _implement_task(self, task: Task, story: Story, project_dir: Path):
        """
        Implement a single task by generating and writing code files.
        """
        self.logger.info(f"Implementing Task #{task.id}: {task.title}")

        # Mark as in progress
        task.status = TaskStatus.IN_PROGRESS
        task.assigned_agent = self.AGENT_NAME
        self.db.commit()

        # Generate code using LLM
        code_files = self._generate_code_for_task(task, story)

        # Write files to disk (with verification)
        for file_info in code_files:
            file_path = project_dir / file_info['path']
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w') as f:
                f.write(file_info['content'])

            # Verify write succeeded
            if not file_path.exists():
                raise IOError(f"File {file_path} was not found after write")
            with open(file_path, 'r') as f:
                if f.read() != file_info['content']:
                    raise IOError(f"File {file_path} content mismatch after write")

            self.logger.info(f"  Wrote: {file_info['path']} ({len(file_info['content'])} chars)")

            # Commit to Git
            self._commit_file(file_path, task, story)

        # Mark as done
        task.status = TaskStatus.DONE
        task.completed_at = datetime.utcnow()
        task.output_json = {
            "files_written": [f['path'] for f in code_files],
            "implementation": "Code generated and written to disk",
        }
        self.db.commit()
        self.emit("finished", story,
                  f"Task #{task.id} complete: {task.title} ({len(code_files)} files)")

        # Add comment
        self.add_comment(
            story,
            f"✅ Task #{task.id} completed: {task.title}\n\nFiles: {', '.join(f['path'] for f in code_files)}",
            comment_type="note",
        )

        self.log_action(
            action="implement_task",
            story=story,
            task=task,
            output={"files": len(code_files)},
        )

    def _generate_code_for_task(self, task: Task, story: Story) -> List[Dict]:
        """
        Use LLM to generate actual code files for a task.
        """
        llm = get_client(self.AGENT_NAME)

        # Determine tech stack based on task title and story context
        tech_stack = self._detect_tech_stack(task, story)

        # Get context with rules from base agent
        # Exclude tasks to reduce context size - we only need current task info
        base_messages = super().build_llm_context(story, exclude_tasks=True)

        # Build user prompt with task details
        user_prompt = f"""Generate code for this task:


**Task ID:** {task.id}
**Task Title:** {task.title}
**Task Description:** {task.description}
**File Path:** {task.output_json.get('file_path', 'N/A')}
**Function Signature:** {task.output_json.get('function_signature', 'N/A')}
**Acceptance Criteria:** {task.output_json.get('acceptance_criteria', 'N/A')}
**Test Strategy:** {task.output_json.get('test_strategy', 'N/A')}
**Tech Stack:** {tech_stack['lang']} ({tech_stack['ext']})


Generate ACTUAL CODE files. Return JSON in this format:
{{
  "files": [
    {{
      "path": "services/exchange_rates.py",
      "content": "# code here"
    }}
  ]
}}

Requirements:
- Generate working, production-ready code
- Follow the EXACT function signature provided — do not modify it
- Implement ALL acceptance criteria — each numbered criterion must be addressed
- Follow the test_strategy for how tests should be structured
- Use best practices for {tech_stack['lang']}
- Include error handling where appropriate
- Add comments for complex logic"""

        # Append user prompt to base messages
        messages = base_messages + [{"role": "user", "content": user_prompt}]

        # Try with higher max_tokens for code generation; retry once on parse failure
        last_error = None
        for attempt in range(2):
            response = llm.chat(messages, temperature=0.3, max_tokens=8192 if attempt == 0 else 16384)

            try:
                from core.json_utils import extract_json
                parsed = extract_json(response)
                if parsed is not None:
                    files = parsed.get("files", [])
                    if files:
                        return files
                last_error = ValueError("No files in parsed JSON response")
            except Exception as e:
                last_error = e
                if attempt == 0:
                    self.logger.warning(f"Parse attempt 1 failed ({e}), retrying with more tokens...")
                    continue

        # FAIL LOUD on code generation failure - do not silently mark task done with no files
        self.logger.error(f"Code generation failed after 2 attempts: {last_error}")
        raise RuntimeError(
            f"Code generation failed for task #{task.id} after 2 attempts: {last_error}. "
            "Task NOT marked complete."
        )

    def _detect_tech_stack(self, task: Task, story: Story) -> Dict:
        """
        Detect which tech stack to use based on task and story.
        """
        task_lower = task.title.lower()
        story_tech = story.context_json.get('tech_stack', {})

        # Flutter tasks
        if any(word in task_lower for word in ['flutter', 'mobile', 'ui', 'screen', 'widget', 'app']):
            return self.TECH_STACKS['flutter']

        # Backend tasks
        if any(word in task_lower for word in ['api', 'endpoint', 'server', 'backend', 'fastapi', 'database', 'service', 'model']):
            # Check if backend tech stack is specified
            backend_lang = story_tech.get('backend', 'python')  # Default to Python
            if backend_lang == 'python' or 'fastapi' in str(story_tech).lower():
                return self.TECH_STACKS['fastapi']
            return self.TECH_STACKS['fastapi']

        # Web tasks
        if any(word in task_lower for word in ['web', 'frontend', 'react', 'html']):
            return self.TECH_STACKS.get('react', self.TECH_STACKS['html'])

        # Default to Python/FastAPI
        return self.TECH_STACKS['fastapi']

    def _commit_file(self, file_path: Path, task: Task, story: Story):
        """
        Commit a file to Git repository.

        Raises:
            RuntimeError: If git add or git commit fails.
        """
        import subprocess

        # git add
        result = subprocess.run(
            ['git', 'add', str(file_path)],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Git add failed for {file_path}: {result.stderr.strip()}"
            )

        # git commit
        result = subprocess.run(
            ['git', 'commit', '-m', f'[aco-dev] {task.title}'],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Git commit failed for {file_path}: {result.stderr.strip()}"
            )

        self.logger.info(f"  Committed: {file_path.name}")

    def _complete_story(self, story: Story, tasks: List[Task]):
        """
        Move story to QA and push to GitHub.
        """
        self.add_comment(
            story,
            f"🎉 **Development Complete!**\n\nAll {len(tasks)} tasks implemented.\n\nReady for QA review.",
            comment_type="note",
        )

        # Push to GitHub
        try:
            branch_name = f"feature/story-{story.id}"
            if hasattr(self.gh, 'create_branch'):
                self.gh.create_branch(branch_name)
            if hasattr(self.gh, 'push_branch'):
                self.gh.push_branch(branch_name)
            self.logger.info(f"Created and pushed branch: {branch_name}")
        except Exception as e:
            self.logger.warning(f"Failed to create/push branch: {e}")

        self.update_story_status(story, StoryStatus.QA)
        self.emit("finished", story,
                  f"All {len(tasks)} tasks done, moving to QA: {story.title}")

        self.log_action(
            action="complete_story",
            story=story,
            output={"tasks_completed": len(tasks)},
        )

        self.logger.info(f"Story #{story.id} development complete, moved to QA")


def main():
    """Run dev agent."""
    agent = DeveloperAgent()
    try:
        agent.run()
    finally:
        agent.close()


if __name__ == "__main__":
    main()
