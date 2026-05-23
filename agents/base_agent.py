"""
Base agent class with shared functionality.
All agents inherit from this.
"""
import json
import structlog
from datetime import datetime
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

from core.database import get_session, Story, Task, StoryStatus, TaskStatus, AgentLog, StoryComment
from config.settings import get_settings
from integrations.github_sync import get_github_sync
from core.event_bus import emit as _emit


logger = structlog.get_logger()


class BaseAgent(ABC):
    """
    Base class for all ACO agents.
    
    Provides:
    - Database access
    - Logging
    - Context management
    - Human communication
    - Error handling
    """
    
    # Override in subclass
    AGENT_NAME: str = "base"
    HANDLES_STATUSES: List[StoryStatus] = []

    def __init__(self, skip_find_work: bool = False):
        self.settings = get_settings()
        self.db = get_session()
        self.logger = structlog.get_logger().bind(agent=self.AGENT_NAME)
        self.github_sync = get_github_sync()

        # NEW: Load agent prompt from markdown (if available)
        try:
            from core.prompt_loader import load_agent_prompt
            self.agent_prompt, self.agent_metadata = load_agent_prompt(self.AGENT_NAME)
            self.logger.info(f"Loaded agent prompt: {self.agent_metadata.get('name')}")
        except Exception as e:
            self.logger.warning(f"Could not load agent prompt from markdown: {e}")
            self.agent_prompt = f"You are the {self.AGENT_NAME} agent."
            self.agent_metadata = {}

        # NEW: Load relevant rules (if available)
        try:
            from core.rule_loader import get_relevant_rules, load_multiple_rules
            self.rule_paths = get_relevant_rules(self.AGENT_NAME)
            self.rules = load_multiple_rules(self.rule_paths)
            self.logger.info(f"Loaded {len(self.rules)} rules: {list(self.rules.keys())}")
        except Exception as e:
            self.logger.warning(f"Could not load rules: {e}")
            self.rules = {}
            self.rule_paths = []

        # NEW: Set allowed tools from metadata
        self.allowed_tools = self.agent_metadata.get("tools", [])

    def run(self):
        """
        Main agent loop. Polls for work and processes it.
        """
        self.logger.info(f"{self.AGENT_NAME} starting...")
        
        while True:
            try:
                # Find work for this agent
                story = self.find_work()
                
                if story:
                    self.logger.info(f"Found work: Story #{story.id} - {story.title}")
                    self.process_story(story)
                    # Expire all cached objects after each story so the next iteration
                    # loads fresh data from the DB. Prevents "Instance not bound to session"
                    # errors after long-running stories or concurrent updates.
                    self.db.expire_all()
                else:
                    # No work, wait and poll again
                    import time
                    self.logger.debug("No work found, polling...")
                    time.sleep(self.settings.AGENT_POLL_INTERVAL_SECONDS)
                    
            except Exception as e:
                self.logger.error(f"Agent error: {e}", exc_info=True)
                import time
                time.sleep(60)  # Wait before retrying
    
    # Stories abandoned if assigned but not updated for this long (seconds)
    STORY_TIMEOUT_SECONDS = 1800  # 30 minutes

    def find_work(self) -> Optional[Story]:
        """
        Find a story that this agent should work on.

        Also releases abandoned stories (assigned but stale for > STORY_TIMEOUT_SECONDS).
        """
        if not self.HANDLES_STATUSES:
            return None

        # First: clean up any abandoned stories
        self._release_abandoned_stories()

        story = (
            self.db.query(Story)
            .filter(Story.status.in_(self.HANDLES_STATUSES))
            .filter(Story.assigned_agent == None)  # Not currently assigned
            .order_by(Story.priority.desc(), Story.created_at.asc())  # Priority FIFO
            .first()
        )

        # Claim the story
        if story:
            story.assigned_agent = self.AGENT_NAME
            story.status = StoryStatus.PM_REVIEW  # Keep current status
            story.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(story)

        return story

    def _release_abandoned_stories(self):
        """
        Release stories that have been assigned but not updated for too long.
        This handles crashed agents that left stories in a locked state.
        """
        cutoff = datetime.utcnow().timestamp() - self.STORY_TIMEOUT_SECONDS
        cutoff_dt = datetime.utcfromtimestamp(cutoff)

        abandoned = (
            self.db.query(Story)
            .filter(Story.assigned_agent != None)
            .filter(Story.updated_at < cutoff_dt)
            .all()
        )

        for story in abandoned:
            self.logger.warning(
                f"Releasing abandoned Story #{story.id} "
                f"(assigned to {story.assigned_agent}, last updated {story.updated_at})"
            )
            self.add_comment(
                story,
                f"⚠️ Story released from `{story.assigned_agent}` — abandoned timeout "
                f"({self.STORY_TIMEOUT_SECONDS // 60}min). Re-queued for assignment.",
                comment_type="note",
            )
            story.assigned_agent = None
            story.updated_at = datetime.utcnow()

        if abandoned:
            self.db.commit()
    
    @abstractmethod
    def process_story(self, story: Story):
        """
        Process a story. Override in subclass.
        
        This is where the agent does its actual work.
        """
        pass
    
    def log_action(
        self,
        action: str,
        story: Optional[Story] = None,
        task: Optional[Task] = None,
        input_context: Optional[Dict] = None,
        output: Optional[Dict] = None,
        decisions: Optional[List] = None,
        questions: Optional[List] = None,
        duration_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ):
        """
        Log an agent action for auditing.
        """
        log_entry = AgentLog(
            agent_id=self.AGENT_NAME,
            action=action,
            story_id=story.id if story else None,
            task_id=task.id if task else None,
            input_context=input_context or {},
            output=output or {},
            decisions_made=decisions or [],
            questions_asked=questions or [],
            duration_ms=duration_ms,
            success=1 if success else 0,
            error_message=error_message,
        )
        
        self.db.add(log_entry)
        self.db.commit()
        
        self.logger.info(
            f"Action logged: {action}",
            story_id=story.id if story else None,
            success=success,
        )
    
    def add_comment(
        self,
        story: Story,
        content: str,
        comment_type: str = "note",
        sync_to_github: bool = True,
    ):
        """
        Add a comment to a story (for conversation history).
        """
        comment = StoryComment(
            story_id=story.id,
            author=self.AGENT_NAME,
            content=content,
            comment_type=comment_type,
        )
        self.db.add(comment)
        self.db.commit()

        # Sync to GitHub if enabled
        if sync_to_github:
            self.sync_comment_to_github(comment, story)

        self.logger.debug(f"Added comment to Story #{story.id}")

    def emit(
        self,
        verb: str,
        story: Optional[Story] = None,
        content: str = "",
        **metadata,
    ):
        """
        Broadcast what this agent is doing to the shared channel.
        This is how you see what agents are "talking about" in real time.
        """
        _emit(
            agent_id=self.AGENT_NAME,
            verb=verb,
            story_id=story.id if story else None,
            content=content,
            metadata=metadata if metadata else None,
        )
    
    def ask_human(
        self,
        story: Story,
        question: str,
        wait_for_answer: bool = True,
    ) -> Optional[str]:
        """
        Ask the human a question about this story.
        
        In the automated ACO System, we use an LLM to simulate the human stakeholder
        so the system remains fully autonomous without manual intervention.
        """
        self.add_comment(story, f"❓ QUESTION: {question}", comment_type="question")
        
        self.log_action(
            action="ask_human",
            story=story,
            input_context={"question": question},
            questions=[question],
        )
        
        self.logger.warning(f"Asked human (simulated): {question}")
        
        # Simulate human response using LLM
        try:
            from integrations.llm_client import get_client
            llm = get_client()

            # Simple prompt to act as the product owner/stakeholder
            system_prompt = "You are the product owner/stakeholder. Please answer the following clarifying question concisely, providing direction to the team. Always approve the general direction unless it contradicts the core purpose of the task."
            user_prompt = f"Story Title: {story.title}\nStory Description: {story.description}\n\nQuestion:\n{question}"

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            answer = llm.chat(messages, temperature=0.7)

            # Add the simulated answer as a comment
            self.add_comment(story, f"👤 STAKEHOLDER ANSWER:\n\n{answer}", comment_type="answer")
            return answer

        except Exception as e:
            self.logger.error(f"Failed to simulate human answer: {e}")
            fallback_answer = "Proceed with your best judgment."
            self.add_comment(story, f"👤 STAKEHOLDER ANSWER (Fallback):\n\n{fallback_answer}", comment_type="answer")
            return fallback_answer
    
    def update_story_status(
        self,
        story: Story,
        new_status: StoryStatus,
        context_update: Optional[Dict] = None,
        sync_to_github: bool = True,
        skip_validation: bool = False,
    ):
        """
        Update a story's status and optionally add context.

        Args:
            story: Story to update
            new_status: New status to set
            context_update: Optional context updates
            sync_to_github: Whether to sync to GitHub
            skip_validation: Skip validation hooks (use carefully!)
        """
        from_status = story.status.value if hasattr(story.status, 'value') else str(story.status)
        to_status = new_status.value if hasattr(new_status, 'value') else str(new_status)

        # Run validation hooks unless explicitly skipped
        if not skip_validation:
            try:
                from core.validation_hooks import validate_story_transition
                passed, messages = validate_story_transition(story, from_status, to_status)

                if not passed:
                    # Validation failed - don't update status
                    error_comment = f'## ❌ Validation Failed\n\nTransition `{from_status} → {to_status}` blocked:\n\n' + '\n'.join(messages)
                    self.add_comment(story, error_comment, comment_type='error')
                    self.logger.warning(f'Validation failed for Story #{story.id}: {messages}')
                    self.release_story(story)
                    return False
            except Exception as e:
                self.logger.error(
                    f"Validation hook raised an exception — blocking transition "
                    f"to prevent unsafe state: {e}",
                    exc_info=True,
                )
                error_comment = (
                    f"## ❌ Validation System Error\n\n"
                    f"Validation hook crashed during `{from_status} → {to_status}` transition: {e}\n"
                    f"Transition blocked for safety. Story remains assigned."
                )
                try:
                    self.add_comment(story, error_comment, comment_type="error")
                except Exception:
                    pass  # DB may be in bad state; don't fail on comment
                # Do NOT release the story — it stays assigned so it can be retried
                # or manually recovered. Releasing it would lose the error context.
                return False

        # Update status
        story.status = new_status
        story.updated_at = datetime.utcnow()

        if context_update:
            from sqlalchemy.orm.attributes import flag_modified
            updated_context = dict(story.context_json or {})
            updated_context.update(context_update)
            story.context_json = updated_context
            flag_modified(story, "context_json")

        # Commit status change FIRST, then release ownership
        # This order matters: if commit fails, story stays owned and can be retried
        self.db.commit()
        story.assigned_agent = None  # Release the story

        # Sync to GitHub if enabled
        if sync_to_github:
            self.sync_to_github(story)

        self.logger.info(
            f"Story #{story.id} status: {story.status.value}",
        )

        return True
    
    def release_story(self, story: Story):
        """
        Release a story without changing status (e.g., on error).
        """
        story.assigned_agent = None
        story.updated_at = datetime.utcnow()
        self.db.commit()

    def sync_to_github(self, story: Story):
        """
        Sync story to GitHub (create issue or update labels).
        """
        try:
            issue_number = story.context_json.get("github_issue_number")

            if not issue_number:
                # Create new issue
                issue_number = self.github_sync.create_issue(story)
                from sqlalchemy.orm.attributes import flag_modified
                updated_context = dict(story.context_json or {})
                updated_context["github_issue_number"] = issue_number
                story.context_json = updated_context
                flag_modified(story, "context_json")
                self.db.commit()
                self.logger.info(f"Created GitHub issue #{issue_number} for Story #{story.id}")
            else:
                # Update existing issue labels
                self.github_sync.update_issue_labels(story, issue_number)
                self.logger.info(f"Updated GitHub issue #{issue_number} labels")

        except Exception as e:
            self.logger.error(f"GitHub sync failed: {e}", exc_info=True)

    def sync_comment_to_github(self, comment: StoryComment, story: Story):
        """
        Sync a comment to GitHub issue.
        """
        try:
            issue_number = story.context_json.get("github_issue_number")
            if not issue_number:
                self.logger.warning(f"No GitHub issue for Story #{story.id}, cannot sync comment")
                return

            self.github_sync.add_comment(story.id, issue_number, comment)
            self.logger.debug(f"Synced comment to GitHub issue #{issue_number}")

        except Exception as e:
            self.logger.error(f"Failed to sync comment to GitHub: {e}", exc_info=True)

    # NEW: Build LLM context with rule injection and context trimming
    def build_llm_context(self, story: Story, exclude_tasks: bool = False) -> List[Dict]:
        """
        Build LLM context with agent prompt, injected rules, and context trimming.
        """
        messages = []

        # Start with agent prompt
        system_content = getattr(self, 'agent_prompt', f"You are the {self.AGENT_NAME} agent.")

        # Add rules if any
        if getattr(self, 'rules', None):
            rules_content = []
            for rule_path, rule_text in self.rules.items():
                rule_name = rule_path.replace("common/", "").replace(".md", "")
                rules_content.append(f"## 🔒 Rule: {rule_name}\n\n{rule_text}")

            # Concatenate rules into system message (single message, not multiple)
            system_content += "\n\n---\n\n## 📋 Rules (MUST Follow)\n\n"
            system_content += "\n\n".join(rules_content)

        messages.append({"role": "system", "content": system_content})

        # Get comments and trim if needed
        comments = story.comments or []
        try:
            from core.context_trimmer import trim_story_context
            trimmed_comments, was_trimmed = trim_story_context(
                [c.to_dict() for c in comments],
                max_tokens=self.settings.MAX_CONTEXT_TOKENS
            )
            if was_trimmed:
                self.logger.info(f"Trimmed comments for Story #{story.id}")
            story_dict = story.to_dict()
            story_dict["comments"] = trimmed_comments
        except Exception as e:
            self.logger.warning(f"Context trimming failed: {e}")
            story_dict = story.to_dict()

        # Add story context (with trimmed comments)
        # Optionally exclude tasks to reduce context size for task-specific agents
        if exclude_tasks:
            story_dict = {
                "id": story.id,
                "title": story.title,
                "description": story.description,
                "status": story.status.value,
                "priority": story.priority,
                "context": story.context_json,
                "acceptance_criteria": story.acceptance_criteria,
            }
        # IMPORTANT: OpenRouter needs string content, not dict
        messages.append({"role": "user", "content": json.dumps(story_dict)})

        return messages

    # NEW: Check tool permission (tool scoping)
    def check_tool_permission(self, tool_name: str) -> bool:
        """
        Check if agent is allowed to use a tool.
        """
        allowed_tools = getattr(self, 'allowed_tools', [])
        if not allowed_tools:
            self.logger.warning(f"Agent {self.AGENT_NAME} has no tools configured")
            return False

        if tool_name not in allowed_tools:
            self.logger.warning(
                f"Agent {self.AGENT_NAME} not allowed to use tool: {tool_name}"
            )
            return False

        return True

    def close(self):
        """
        Clean up resources.
        """
        self.db.close()
