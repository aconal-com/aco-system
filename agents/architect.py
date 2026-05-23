"""
Architect Agent (aco-architect)

Responsibilities:
- Review stories and task breakdowns for technical feasibility
- Identify architectural concerns, risks, gaps
- Approve or reject stories before development
- Add technical guidance and constraints

Workflow:
1. Pick up story with status "ready-architect"
2. Review story + tasks from planner
3. Use LLM to analyze feasibility
4. Either:
   - Approve → Mark as "approved"
   - Reject → Send back to PM with comments
"""
import json
from datetime import datetime
from typing import List, Dict, Any

from agents.base_agent import BaseAgent
from core.database import Story, Task, StoryStatus, TaskStatus
from integrations.llm_client import get_client


class ArchitectAgent(BaseAgent):
    AGENT_NAME = "aco-architect"
    HANDLES_STATUSES = [StoryStatus.READY_ARCHITECT]
    
    def process_story(self, story: Story):
        """
        Review and approve/reject a story for development.
        """
        try:
            self.emit("picked_up", story, f"Starting architecture review: {story.title}")
            self.logger.info(f"Architect reviewing Story #{story.id}: {story.title}")
            
            # Get tasks for this story
            tasks = (
                self.db.query(Task)
                .filter(Task.story_id == story.id)
                .order_by(Task.id.asc())
                .all()
            )
            
            # Build review context
            review_context = self._build_review_context(story, tasks)

            # Ask LLM to review
            llm = get_client(self.AGENT_NAME)
            review_result = self._get_review_from_llm(llm, story, tasks)
            
            # Make decision
            if review_result.get("approved", False):
                self._approve_story(story, review_result)
            elif review_result.get("missing_tasks"):
                # Missing tasks is NOT a blocker - approve with missing tasks
                # PM will auto-add them in the next pass
                self._approve_with_missing_tasks(story, review_result)
            else:
                # True blocker - reject and send back to PM
                self._reject_story(story, tasks, review_result)
            
        except Exception as e:
            self.logger.error(f"Error in architect review: {e}", exc_info=True)
            self.release_story(story)
            raise
    
    def _build_review_context(self, story: Story, tasks: List[Task]) -> Dict:
        """Build context for architectural review."""
        return {
            "story": {
                "id": story.id,
                "title": story.title,
                "description": story.description,
                "acceptance_criteria": story.acceptance_criteria,
                "context": story.context_json,
            },
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "estimate_hours": t.estimate_hours,
                    "dependencies": t.dependencies,
                }
                for t in tasks
            ],
        }
    
    def _get_review_from_llm(self, llm, story: Story, tasks: List[Task]) -> Dict:
        """Use LLM to review the story architecture."""

        system_prompt = """You are a senior software architect reviewing story plans BEFORE development begins.

**Your role is PLAN REVIEW, not code review.** You evaluate whether the planned approach can deliver the described functionality. You are NOT looking for code-level bugs (N+1 queries, SQL injection, race conditions, hardcoded secrets) — those don't exist yet.

**Approval Rule: APPROVE unless there is a FUNDAMENTAL BLOCKER.**

Reject only if:
1. Tech stack CANNOT physically achieve a core requirement
2. Critical tasks are completely missing (e.g., no authentication when auth is required)
3. Plan fundamentally contradicts itself (e.g., "offline-only" + "requires real-time sync")

For ALL other concerns — APPROVE with recommendations. It is better to build something imperfect and iterate than to get stuck in review loops.

Output ONLY valid JSON:
{
  "approved": true/false,
  "reasoning": "Brief analysis of plan feasibility and coherence",
  "concerns": ["minor concern 1 - not a blocker"],
  "recommendations": ["recommendation 1"],
  "missing_tasks": ["task that should be added if critical"],
  "technical_guidance": "Architecture notes for developers"
}"""

        task_summaries = [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "estimate_hours": t.estimate_hours,
                "dependencies": t.dependencies,
            }
            for t in tasks
        ]

        user_prompt = f"""Review this story and task breakdown:

**Story:** {story.title}

**Description:**
{story.description}

**Acceptance Criteria:**
{json.dumps(story.acceptance_criteria or [], indent=2)}

**Planned Tasks:**
{json.dumps(task_summaries, indent=2)}

**Additional Context:**
{json.dumps(story.context_json or {}, indent=2)}

Review the plan for technical feasibility and coherence.
- APPROVE if the tech stack can deliver the requirements
- Only REJECT if there is a fundamental impossibility
- For concerns, add as recommendations (do not reject)

Return ONLY the JSON."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = llm.chat(messages, temperature=0.2)

        # Handle None or empty response - auto-reject
        if not response:
            self.logger.warning("LLM returned empty response, auto-rejecting story")
            return {
                "approved": False,
                "reasoning": "LLM returned empty response, story requires human review",
                "risks": ["LLM failure"],
                "recommendations": ["Retry with valid LLM response"],
                "missing_tasks": [],
                "technical_guidance": "",
            }

        # Parse JSON — use extract_json to handle } inside strings correctly
        from core.json_utils import extract_json
        try:
            parsed = extract_json(response)
            # If parsed is a list (LLM returned array instead of object), take first dict element
            if isinstance(parsed, list):
                parsed = next((item for item in parsed if isinstance(item, dict)), None)
            if parsed is not None and isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        # Fallback: reject if we couldn't parse — don't auto-approve with garbage
        self.logger.error(f"Architect could not parse LLM response as JSON for Story #{story.id}")
        return {
            "approved": False,
            "reasoning": "LLM response was not valid JSON — manual review required",
            "risks": ["JSON parsing failed"],
            "recommendations": ["Retry with a valid LLM response"],
            "missing_tasks": [],
            "technical_guidance": "",
        }
    
    def _approve_story(self, story: Story, review_result: Dict):
        """Approve the story for development."""

        # Add architect's guidance to context
        story.context_json["architect_approval"] = {
            "approved_at": datetime.utcnow().isoformat(),
            "approved_by": self.AGENT_NAME,
            "reasoning": review_result.get("reasoning", ""),
            "concerns": review_result.get("concerns", []),
            "recommendations": review_result.get("recommendations", []),
            "technical_guidance": review_result.get("technical_guidance", ""),
        }

        comment = f"✅ **APPROVED** by Architect\n\n"
        comment += f"{review_result.get('reasoning', 'Plan approved for development')}\n\n"

        if review_result.get("recommendations"):
            comment += "**Recommendations:**\n"
            for rec in review_result["recommendations"]:
                comment += f"- {rec}\n"

        if review_result.get("technical_guidance"):
            comment += f"\n**Technical Guidance:**\n{review_result['technical_guidance']}\n"

        self.add_comment(story, comment, comment_type="decision")

        # Validation is automatic in BaseAgent.update_story_status()
        self.update_story_status(story, StoryStatus.APPROVED)
        self.emit("approved", story, f"Story approved for development: {story.title}")

        self.log_action(
            action="approve_story",
            story=story,
            output=review_result,
            decisions=["approved"],
        )

        self.logger.info(f"Story #{story.id} approved for development")

    def _approve_with_missing_tasks(self, story: Story, review_result: Dict):
        """Approve story and auto-create missing tasks discovered during review."""
        from sqlalchemy.orm.attributes import flag_modified

        # Auto-create missing tasks
        missing_tasks = review_result.get("missing_tasks", [])
        created_tasks = []
        for i, task_title in enumerate(missing_tasks, 1):
            task = Task(
                story_id=story.id,
                title=task_title,
                description=f"Auto-added by architect: {task_title}",
                estimate_hours=4,  # Default estimate
                dependencies=[],
                status=TaskStatus.TODO,
                output_json={"auto_added": True},
            )
            self.db.add(task)
            created_tasks.append(task)

        if created_tasks:
            self.db.commit()
            for task in created_tasks:
                self.db.refresh(task)
            self.logger.info(f"Auto-created {len(created_tasks)} missing tasks")

        # Update context
        updated_context = dict(story.context_json or {})
        updated_context["architect_approval"] = {
            "approved_at": datetime.utcnow().isoformat(),
            "approved_by": self.AGENT_NAME,
            "reasoning": review_result.get("reasoning", ""),
            "with_missing_tasks": True,
            "missing_tasks_added": len(created_tasks),
            "recommendations": review_result.get("recommendations", []),
        }
        story.context_json = updated_context
        flag_modified(story, "context_json")

        comment = f"✅ **APPROVED** by Architect\n\n"
        comment += f"{review_result.get('reasoning', 'Plan approved')}\n\n"
        if created_tasks:
            comment += f"**Auto-added {len(created_tasks)} missing tasks:**\n"
            for task in created_tasks:
                comment += f"- {task.title}\n"
        if review_result.get("recommendations"):
            comment += "\n**Recommendations:**\n"
            for rec in review_result["recommendations"]:
                comment += f"- {rec}\n"
        if review_result.get("technical_guidance"):
            comment += f"\n**Technical Guidance:**\n{review_result['technical_guidance']}\n"

        self.add_comment(story, comment, comment_type="decision")
        self.update_story_status(story, StoryStatus.APPROVED)
        self.emit("approved", story,
                  f"Story approved with {len(created_tasks)} auto-added tasks: {story.title}")

        self.log_action(
            action="approve_with_missing_tasks",
            story=story,
            output=review_result,
            decisions=["approved_with_missing_tasks"],
        )

        self.logger.info(f"Story #{story.id} approved with {len(created_tasks)} auto-added tasks")

    def _reject_story(self, story: Story, tasks: List[Task], review_result: Dict):
        """Reject the story and send back to PM."""

        # Add rejection details to context
        story.context_json["architect_rejection"] = {
            "rejected_at": datetime.utcnow().isoformat(),
            "reasoning": review_result.get("reasoning", ""),
            "missing_tasks": review_result.get("missing_tasks", []),
            "recommendations": review_result.get("recommendations", []),
        }

        # Build rejection comment
        comment = f"❌ **REJECTED** by Architect\n\n"
        comment += f"**Reasoning:** {review_result.get('reasoning', 'Needs revision')}\n\n"

        if review_result.get("missing_tasks"):
            comment += "**Missing Tasks:**\n"
            for task in review_result["missing_tasks"]:
                comment += f"- {task}\n"
            comment += "\n"

        if review_result.get("recommendations"):
            comment += "**Recommendations:**\n"
            for rec in review_result["recommendations"]:
                comment += f"- {rec}\n"

        self.add_comment(story, comment, comment_type="decision")

        # Send back to PM
        self.update_story_status(story, StoryStatus.PM_REVIEW)
        self.emit("returned", story,
                  f"Story rejected by architect, returned to PM: {story.title}")

        self.log_action(
            action="reject_story",
            story=story,
            output=review_result,
            decisions=["rejected"],
            questions=review_result.get("missing_tasks", []),
        )

        self.logger.warning(f"Story #{story.id} rejected, sent back to PM")


def main():
    """Run the architect agent."""
    agent = ArchitectAgent()
    try:
        agent.run()
    finally:
        agent.close()


if __name__ == "__main__":
    main()
