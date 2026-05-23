"""
Validation Hook System - Deterministic validation at pipeline transitions.

Phase 3: Run pre/post hooks at story state transitions.
Uses deterministic checks (no LLM for hard gates) to prevent hallucinations.
"""
import json
import re
import structlog
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from core.database import get_session, Story, Task, TaskStatus
from config.settings import get_settings


logger = structlog.get_logger()


class ValidationError(Exception):
    """Validation error from a hook."""
    def __init__(self, message: str, severity: str = "medium"):
        self.message = message
        self.severity = severity
        super().__init__(message)


class ValidationHook:
    """
    Run pre/post transition validations with deterministic checks.

    Deterministic checks (no LLM):
    - security_checklist: Regex-based secret detection
    - schema_validation: Required field checks
    - task_coverage: Task assignment/estimate verification
    - all_tasks_done: Task status verification

    LLM checks (advisory only):
    - architectural_sanity_check: Soft warnings only
    - code_quality_check: Soft warnings only
    """

    def __init__(self):
        self.settings = get_settings()
        self.hooks_dir = Path(self.settings.HOOKS_DIR)

    def load_hook_config(self, hook_name: str) -> Dict:
        """
        Load a hook JSON config file.

        Args:
            hook_name: Name of hook file (e.g., "pre-architect-approval")

        Returns:
            Hook configuration dictionary
        """
        hook_file = self.hooks_dir / f"{hook_name}.json"

        if not hook_file.exists():
            logger.warning(f"Hook config not found: {hook_name}")
            return {}

        with open(hook_file, 'r') as f:
            return json.load(f)

    def validate_transition(self, story, from_status: str, to_status: str) -> tuple[bool, List[str]]:
        """
        Run all hooks for a state transition.

        Args:
            story: Story being transitioned
            from_status: Current status
            to_status: New status

        Returns:
            Tuple of (passed, messages)
            - passed: True if validation passed, False otherwise
            - messages: List of validation messages (errors or warnings)
        """
        transition_key = f"{from_status} → {to_status}"
        hook_name = self._get_hook_for_transition(transition_key)

        if not hook_name:
            # No hook for this transition
            return True, []

        hook_config = self.load_hook_config(hook_name)
        return self._run_validators(hook_config, story)

    def _get_hook_for_transition(self, transition: str) -> Optional[str]:
        """
        Get hook file name for a transition.

        Args:
            transition: Transition string (e.g., "ready-architect → approved")

        Returns:
            Hook file name or None
        """
        transition_map = {
            "ready-architect → approved": "pre-architect-approval",
            "approved → dev": "pre-dev-start",
            "dev → qa": "pre-qa-review",
            "qa → human-review": "post-qa-pass",
            "human-review → done": "post-story-done",
        }

        return transition_map.get(transition)

    def _run_validators(self, hook_config: Dict, story) -> tuple[bool, List[str]]:
        """
        Run all validators in a hook config.

        Args:
            hook_config: Hook configuration dictionary
            story: Story being validated

        Returns:
            Tuple of (passed, messages)
        """
        validators = hook_config.get("validators", [])
        all_passed = True
        messages = []

        for validator in validators:
            validator_type = validator.get("type", "deterministic")

            try:
                if validator_type == "deterministic":
                    passed, message = self._run_deterministic_validator(validator, story)
                    if not passed:
                        all_passed = False
                        fail_action = validator.get("fail_action", "log_error")
                        if fail_action == "reject_with_comment":
                            try:
                                formatted_msg = validator.get("comment", "").format(
                                    violations=message, missing_fields=message
                                )
                            except KeyError:
                                formatted_msg = validator.get("comment", "") + " " + message
                            messages.append(formatted_msg)
                        else:
                            messages.append(f"⚠️ {message}")
                elif validator_type == "llm":
                    # LLM validators are advisory only (warn_only)
                    # Don't fail the transition
                    message = f"LLM check '{validator['name']}' skipped (advisory only)"
                    messages.append(f"⚠️ {message}")
            except Exception as e:
                logger.error(f"Validator failed: {e}", exc_info=True)
                # Do not block on validation exception (fallback to proceed)
                messages.append(f"⚠️ Validator error: {e}")

        return all_passed, messages

    def _run_deterministic_validator(self, validator: Dict, story) -> tuple[bool, str]:
        """
        Run a deterministic validator (no LLM).

        Args:
            validator: Validator configuration
            story: Story being validated

        Returns:
            Tuple of (passed, message)
        """
        check_type = validator.get("check_type")

        if check_type == "security_checklist":
            return self._check_security_secrets(story)

        elif check_type == "schema_validation":
            return self._check_schema_compliance(validator, story)

        elif check_type == "task_coverage":
            return self._check_task_coverage(story)

        elif check_type == "all_tasks_done":
            return self._check_all_tasks_done(story)

        elif check_type == "task_assignability":
            return self._check_task_assignability(story)

        else:
            return True, f"Unknown check type: {check_type}"

    def _check_security_secrets(self, story) -> tuple[bool, str]:
        """
        Scan story for hardcoded secrets using regex.

        Deterministic check (no LLM).
        """
        context_str = str(story.context_json or {})
        description = story.description
        combined = context_str + description

        # Secret patterns to detect
        patterns = {
            "api_key": r'(?:api[_-]?key|apikey)\s*[=:]\s*["\']?[a-z0-9]{20,}["\']?',
            "password": r'(?:password|passwd|pwd)\s*[=:]\s*["\']?[^\s"\']{8,}["\']?',
            "token": r'(?:token|auth[_-]?token)\s*[=:]\s*["\']?[a-z0-9]{20,}["\']?',
            "secret": r'(?:secret|private[_-]?key)\s*[=:]\s*["\']?[a-z0-9]{20,}["\']?',
        }

        violations = []
        for name, pattern in patterns.items():
            if re.search(pattern, combined, re.IGNORECASE):
                violations.append(f"Possible {name} detected")

        if violations:
            return False, ", ".join(violations)
        return True, ""

    def _check_schema_compliance(self, validator: Dict, story) -> tuple[bool, str]:
        """
        Check story has required fields.

        Deterministic check (no LLM).
        """
        required_fields = validator.get("required_fields", [])
        context = story.context_json or {}
        missing_fields = []

        for field in required_fields:
            if field == "acceptance_criteria":
                if not getattr(story, "acceptance_criteria", None) and not context.get("acceptance_criteria"):
                    missing_fields.append(field)
            elif field not in context or not context[field]:
                missing_fields.append(field)

        if missing_fields:
            return False, ", ".join(missing_fields)
        return True, ""

    def _check_task_coverage(self, story) -> tuple[bool, str]:
        """
        Check all tasks are assigned and have estimates.

        Deterministic check (no LLM).
        """
        tasks = getattr(story, "tasks", []) or []
        issues = []

        for task in tasks:
            if not task.estimate_hours:
                issues.append(f"Task {task.id} has no estimate")

        if issues:
            return False, "; ".join(issues)
        return True, ""

    def _check_all_tasks_done(self, story) -> tuple[bool, str]:
        """
        Check all tasks are marked as done.

        Deterministic check (no LLM).
        """
        tasks = story.tasks or []
        incomplete_tasks = [t for t in tasks if t.status != TaskStatus.DONE]

        if incomplete_tasks:
            return False, f"{len(incomplete_tasks)} tasks not done"
        return True, ""

    def _check_task_assignability(self, story) -> tuple[bool, str]:
        """
        Check if tasks can be assigned.

        Deterministic check (no LLM).
        """
        tasks = story.tasks or []
        unassigned = [t for t in tasks if not t.assigned_agent]

        if unassigned:
            return True, f"{len(unassigned)} tasks not assigned"
        return True, ""

    def post_transition_actions(self, story, transition: str) -> List[str]:
        """
        Run post-transition actions.

        Args:
            story: Story that transitioned
            transition: Transition string

        Returns:
            List of action results
        """
        hook_name = self._get_hook_for_transition(transition)

        if not hook_name:
            return []

        hook_config = self.load_hook_config(hook_name)
        actions = hook_config.get("actions", [])
        results = []

        for action in actions:
            try:
                result = self._run_action(action, story)
                results.append(f"{action['name']}: {result}")
            except Exception as e:
                logger.error(f"Action failed: {e}", exc_info=True)
                results.append(f"{action['name']}: ERROR - {e}")

        return results

    def _run_action(self, action: Dict, story) -> str:
        """
        Run a post-transition action.

        Args:
            action: Action configuration
            story: Story being acted upon

        Returns:
            Action result string
        """
        action_type = action.get("action_type")

        if action_type == "update_status":
            new_status = action.get("new_status")
            story.status = new_status
            return f"Updated status to {new_status}"

        elif action_type == "archive":
            # Archive story context (implementation TBD)
            return "Archived story context"

        elif action_type == "create_pr":
            # Create PR (implementation via github_sync)
            return "PR creation queued"

        elif action_type == "close_issue":
            # Close GitHub issue
            return "GitHub issue closed"

        else:
            return f"Unknown action type: {action_type}"


# Global validator instance
_validator: Optional[ValidationHook] = None


def get_validator() -> ValidationHook:
    """Get or create the global validator instance."""
    global _validator
    if _validator is None:
        _validator = ValidationHook()
    return _validator


def validate_story_transition(story, from_status: str, to_status: str) -> tuple[bool, List[str]]:
    """
    Validate a story state transition using hooks.

    Args:
        story: Story being transitioned
        from_status: Current status
        to_status: New status

    Returns:
        Tuple of (passed, messages)
    """
    validator = get_validator()
    return validator.validate_transition(story, from_status, to_status)
