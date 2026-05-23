"""
Human Review Agent (aco-human)

Responsibilities:
- Final review before marking work complete
- Think like a human user/stakeholder
- Validate the work meets real-world needs
- Approve or escalate to human (Aniket)

Workflow:
1. Pick up story with status "human-review"
2. Review all work holistically
3. Either:
   - Approve → Mark as "done"
   - Reject → Send back with feedback
   - Escalate → Ping human for decision
"""
import json
from datetime import datetime
from typing import List, Dict, Any

from agents.base_agent import BaseAgent
from core.database import Story, Task, StoryStatus, TaskStatus
from integrations.llm_client import get_client


class HumanReviewerAgent(BaseAgent):
    AGENT_NAME = "aco-human"
    HANDLES_STATUSES = [StoryStatus.HUMAN_REVIEW]
    
    def process_story(self, story: Story):
        """
        Final human-like review before completion.
        """
        try:
            self.emit("picked_up", story, f"Starting human review: {story.title}")
            self.logger.info(f"Human review for Story #{story.id}: {story.title}")
            
            # Get all tasks
            tasks = (
                self.db.query(Task)
                .filter(Task.story_id == story.id)
                .all()
            )
            
            # Build review context
            context = self._build_review_context(story, tasks)
            
            # Use LLM to do human-like review
            llm = get_client(self.AGENT_NAME)
            review_result = self._get_review_from_llm(llm, context)
            
            # Make decision
            decision = review_result.get("decision", "approve")
            
            if decision == "approve":
                self._approve_story(story, review_result)
            elif decision == "reject":
                self._reject_story(story, tasks, review_result)
            elif decision == "escalate":
                self._escalate_to_human(story, tasks, review_result)
            
        except Exception as e:
            self.logger.error(f"Error in human review: {e}", exc_info=True)
            self.release_story(story)
            raise
    
    def _build_review_context(self, story: Story, tasks: List[Task]) -> Dict:
        """Build context for human review."""
        return {
            "story": {
                "id": story.id,
                "title": story.title,
                "description": story.description,
                "acceptance_criteria": story.acceptance_criteria,
                "priority": story.priority,
            },
            "full_journey": {
                "pm_context": story.context_json.get("pm_summary", {}),
                "planner_context": story.context_json.get("planner_summary", {}),
                "architect_context": story.context_json.get("architect_approval", {}),
                "dev_context": story.context_json.get("development_summary", {}),
                "qa_context": story.context_json.get("qa_approval", {}),
            },
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "output": t.output_json,
                }
                for t in tasks
            ],
            "all_comments": [
                {
                    "author": c.author,
                    "content": c.content,
                    "type": c.comment_type,
                }
                for c in story.comments
            ],
        }
    
    def _get_review_from_llm(self, llm, context: Dict) -> Dict:
        """Use LLM to do human-like review."""
        
        system_prompt = """You are the final AI reviewer for a development team, simulating the human stakeholder.
Think like a real user or stakeholder, not a robot. We are fully autonomous so manual intervention is disabled.

Your job:
1. **Holistic Review**: Does this actually solve the problem?
2. **User Perspective**: Would a real user find this valuable?
3. **Quality Bar**: Is this production-ready?
4. **Edge Cases**: What might break in the real world?
5. **Business Value**: Does this deliver real value?

You have TWO options (do NOT escalate, make the decision yourself):
- **APPROVE**: Work is excellent, mark as done.
- **REJECT**: Send back with specific feedback (not good enough).

Output ONLY valid JSON:
{
  "decision": "approve"|"reject",
  "reasoning": "Your analysis",
  "feedback": ["specific feedback points"],
  "confidence": "high"|"medium"|"low"
}"""

        user_prompt = f"""Do a final human-like review:

**Story:** {context['story']['title']}

**Description:**
{context['story']['description']}

**Acceptance Criteria:**
{json.dumps(context['story']['acceptance_criteria'], indent=2)}

**Full Journey:**
{json.dumps(context['full_journey'], indent=2)}

**All Comments/Decisions:**
{json.dumps(context['all_comments'], indent=2)}

**Completed Tasks:**
{json.dumps(context['tasks'], indent=2)}

Think critically. You're the last gate before this goes live.
If you have ANY doubts, escalate to the human.

Return ONLY the JSON."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        response = llm.chat(messages, temperature=0.3)

        # Parse JSON — fail closed on parse errors
        from core.json_utils import extract_json
        try:
            parsed = extract_json(response)
            if parsed is not None:
                return parsed
            raise ValueError("extract_json returned None")
        except Exception as exc:
            self.logger.error(f"Human review parse failed: {exc}")
            return {
                "decision": "escalate",
                "reasoning": f"Parse error in review response: {exc}. Escalated for human review.",
                "confidence": "low",
            }
    
    def _approve_story(self, story: Story, review_result: Dict):
        """Approve and mark as done."""
        
        story.context_json["human_approval"] = {
            "approved_at": datetime.utcnow().isoformat(),
            "approved_by": self.AGENT_NAME,
            "reasoning": review_result.get("reasoning", ""),
            "confidence": review_result.get("confidence", "high"),
        }
        
        story.status = StoryStatus.DONE
        story.completed_at = datetime.utcnow()
        story.assigned_agent = None
        self.db.commit()
        
        self.add_comment(
            story,
            f"🎉 **APPROVED - COMPLETE!**\n\n"
            f"{review_result.get('reasoning', 'Work approved and complete.')}\n\n"
            f"Story #{story.id} is now DONE.",
            comment_type="decision",
        )
        
        self.update_story_status(story, StoryStatus.DONE)
        self.emit("done", story, f"Story complete: {story.title}")
        
        self.log_action(
            action="human_approve",
            story=story,
            output=review_result,
            decisions=["approved"],
        )
        
        self.logger.info(f"Story #{story.id} approved and complete!")
    
    def _reject_story(self, story: Story, tasks: List[Task], review_result: Dict):
        """Reject and send back."""
        
        story.context_json["human_rejection"] = {
            "rejected_at": datetime.utcnow().isoformat(),
            "reasoning": review_result.get("reasoning", ""),
            "feedback": review_result.get("feedback", []),
        }
        
        # Determine where to send back (probably to dev or PM)
        # For now, send to PM for re-evaluation
        target_status = StoryStatus.PM_REVIEW
        
        comment = f"❌ **REJECTED** by Human Reviewer\n\n"
        comment += f"**Reasoning:** {review_result.get('reasoning', 'Needs revision')}\n\n"
        
        if review_result.get("feedback"):
            comment += "**Feedback:**\n"
            for fb in review_result["feedback"]:
                comment += f"- {fb}\n"
        
        self.add_comment(story, comment, comment_type="decision")
        self.update_story_status(story, target_status)
        
        self.log_action(
            action="human_reject",
            story=story,
            output=review_result,
            decisions=["rejected"],
        )
        
        self.logger.warning(f"Story #{story.id} rejected by human reviewer")
    
    def _escalate_to_human(self, story: Story, tasks: List[Task], review_result: Dict):
        """Escalate to actual human (Aniket) for decision."""
        
        story.context_json["human_escalation"] = {
            "escalated_at": datetime.utcnow().isoformat(),
            "reasoning": review_result.get("reasoning", ""),
            "human_ping_message": review_result.get("human_ping_message", ""),
        }
        
        # Add comment that pings the human
        ping_message = review_result.get("human_ping_message", "Needs your input")
        
        comment = f"⚠️ **ESCALATED TO @Aniket**\n\n"
        comment += f"**Why:** {review_result.get('reasoning', 'Needs human judgment')}\n\n"
        comment += f"**Message:** {ping_message}\n\n"
        comment += f"Please review and provide guidance."
        
        self.add_comment(story, comment, comment_type="question")
        
        # Keep in human-review status until human responds
        self.release_story(story)
        
        self.log_action(
            action="human_escalate",
            story=story,
            output=review_result,
            questions=[ping_message],
        )
        
        self.logger.warning(f"Story #{story.id} escalated to human")


def main():
    """Run the human reviewer agent."""
    agent = HumanReviewerAgent()
    try:
        agent.run()
    finally:
        agent.close()


if __name__ == "__main__":
    main()
