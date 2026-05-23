"""
QA Agent (aco-qa)

Responsibilities:
- Review completed development work
- Write and run tests
- Validate acceptance criteria are met
- Approve or reject work

Workflow:
1. Pick up story with status "qa"
2. Review implementation
3. Generate and run tests
4. If all pass → Mark as "human-review"
5. If issues → Send back to dev with feedback
"""
import json
from datetime import datetime
from typing import List, Dict, Any

from agents.base_agent import BaseAgent
from core.database import Story, Task, StoryStatus, TaskStatus
from integrations.llm_client import get_client


class QAAgent(BaseAgent):
    AGENT_NAME = "aco-qa"
    HANDLES_STATUSES = [StoryStatus.QA]
    
    def process_story(self, story: Story):
        """
        QA review of completed development work.
        """
        try:
            self.emit("picked_up", story, f"Starting QA review: {story.title}")
            self.logger.info(f"QA reviewing Story #{story.id}: {story.title}")
            
            # Get tasks for this story
            tasks = (
                self.db.query(Task)
                .filter(Task.story_id == story.id)
                .all()
            )
            
            # Build review context
            context = self._build_review_context(story, tasks)
            
            # Use LLM to review
            llm = get_client(self.AGENT_NAME)
            review_result = self._get_review_from_llm(llm, context)
            
            # Generate tests
            tests = self._generate_tests(llm, story, tasks)
            
            # Make decision
            if review_result.get("passed", True) and not review_result.get("blocking_issues", []):
                self._approve_story(story, review_result, tests)
            else:
                self._reject_story(story, tasks, review_result)
            
        except Exception as e:
            self.logger.error(f"Error in QA review: {e}", exc_info=True)
            self.release_story(story)
            raise
    
    def _build_review_context(self, story: Story, tasks: List[Task]) -> Dict:
        """Build context for QA review."""
        return {
            "story": {
                "id": story.id,
                "title": story.title,
                "description": story.description,
                "acceptance_criteria": story.acceptance_criteria,
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
            "architect_guidance": story.context_json.get("architect_approval", {}),
            "development_summary": story.context_json.get("development_summary", {}),
        }
    
    def _get_review_from_llm(self, llm, context: Dict) -> Dict:
        """Use LLM to review the implementation."""
        
        system_prompt = """You are a senior QA engineer reviewing completed development work.
Your job is to ensure quality before work goes to human review.

Review criteria:
1. **Acceptance Criteria**: Are ALL acceptance criteria met?
2. **Completeness**: Is the implementation complete?
3. **Quality**: Is the code well-structured and maintainable?
4. **Edge Cases**: Are edge cases handled?
5. **Testing**: Are there adequate tests?

You can either:
- **PASS**: Work is ready for human review
- **FAIL**: Send back to dev with specific issues

Output ONLY valid JSON:
{
  "passed": true/false,
  "reasoning": "Your analysis",
  "blocking_issues": ["issue 1", "issue 2"],
  "minor_issues": ["minor issue 1"],
  "test_coverage": "assessment of test coverage",
  "recommendations": ["rec 1", "rec 2"]
}"""

        user_prompt = f"""Review this completed work:

**Story:** {context['story']['title']}

**Description:**
{context['story']['description']}

**Acceptance Criteria:**
{json.dumps(context['story']['acceptance_criteria'], indent=2)}

**Completed Tasks:**
{json.dumps(context['tasks'], indent=2)}

**Architect Guidance:**
{json.dumps(context['architect_guidance'], indent=2)}

Review thoroughly. Check each acceptance criterion explicitly.
If ANY acceptance criterion is not met, fail the review.

Return ONLY the JSON."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        response = llm.chat(messages, temperature=0.2)
        
        # Parse JSON - FAIL CLOSED on parse errors (do not default to pass)
        from core.json_utils import extract_json
        try:
            parsed = extract_json(response)
            # If parsed is a list (LLM returned array instead of object), take first dict element
            if isinstance(parsed, list):
                parsed = next((item for item in parsed if isinstance(item, dict)), None)
            if parsed is not None and isinstance(parsed, dict):
                return parsed
            # None, wrong type, or empty — fail closed
            raise ValueError(f"extract_json returned {type(parsed).__name__}")
        except Exception as e:
            self.logger.error(f"QA review parse failed: {e}")
            return {
                "passed": False,
                "reasoning": f"QA review failed - could not parse LLM response: {e}. Manual review required.",
                "blocking_issues": ["QA system error - manual review required"],
            }
    
    def _generate_tests(self, llm, story: Story, tasks: List[Task]) -> List[Dict]:
        """Generate test cases for the implementation."""
        
        system_prompt = """You are a QA engineer writing test cases.
Generate comprehensive test cases covering:
- Happy path
- Edge cases
- Error handling
- Integration points

Output as a list of test cases."""

        user_prompt = f"""Write test cases for:

**Story:** {story.title}
{story.description}

**Acceptance Criteria:**
{json.dumps(story.acceptance_criteria, indent=2)}

**Implementation:**
{json.dumps([t.output_json for t in tasks], indent=2)}

Generate test cases. For each test include:
- name: Test name
- description: What it tests
- steps: Test steps
- expected: Expected result

Return as JSON array."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        try:
            response = llm.chat(messages, temperature=0.3)
            from core.json_utils import extract_json
            parsed = extract_json(response)
            if parsed is not None and isinstance(parsed, list):
                return parsed
            return []
        except:
            return []
    
    def _approve_story(self, story: Story, review_result: Dict, tests: List[Dict]):
        """Approve and send to human review."""
        
        story.context_json["qa_approval"] = {
            "approved_at": datetime.utcnow().isoformat(),
            "passed": review_result.get("passed", True),
            "reasoning": review_result.get("reasoning", ""),
            "test_cases_generated": len(tests),
        }
        
        self.add_comment(
            story,
            f"✅ **QA PASSED**\n\n"
            f"{review_result.get('reasoning', 'All acceptance criteria met.')}\n\n"
            f"Generated {len(tests)} test cases. Ready for human review.",
            comment_type="decision",
        )
        
        self.update_story_status(story, StoryStatus.HUMAN_REVIEW)
        self.emit("approved", story, f"QA passed: {story.title}")
        
        self.log_action(
            action="qa_approve",
            story=story,
            output=review_result,
            decisions=["approved"],
        )
        
        self.logger.info(f"Story #{story.id} passed QA, sent to human review")
    
    # Maximum QA rejections before escalating to human
    MAX_QA_REJECTIONS = 3

    def _reject_story(self, story: Story, tasks: List[Task], review_result: Dict):
        """Reject and send back to dev, or escalate if max rejections reached."""

        # Track rejection count
        rejection_count = story.context_json.get("qa_rejection_count", 0) + 1
        story.context_json["qa_rejection_count"] = rejection_count

        # Escalate after MAX_QA_REJECTIONS
        if rejection_count >= self.MAX_QA_REJECTIONS:
            self.add_comment(
                story,
                f"🚨 **QA REJECTION ESCALATION** ({rejection_count}/{self.MAX_QA_REJECTIONS}): "
                f"Story rejected {rejection_count} times. Manual intervention required.",
                comment_type="error",
            )
            self.update_story_status(story, StoryStatus.HUMAN_REVIEW)
            self.emit("escalated", story,
                      f"QA escalated after {rejection_count} rejections: {story.title}")
            self.logger.warning(
                f"Story #{story.id} escalated to human after {rejection_count} QA rejections"
            )
            return

        story.context_json["qa_rejection"] = {
            "rejected_at": datetime.utcnow().isoformat(),
            "blocking_issues": review_result.get("blocking_issues", []),
            "minor_issues": review_result.get("minor_issues", []),
            "attempt": rejection_count,
        }
        
        # Build rejection comment
        comment = f"❌ **QA FAILED**\n\n"
        comment += f"**Reasoning:** {review_result.get('reasoning', 'Issues found')}\n\n"
        
        if review_result.get("blocking_issues"):
            comment += "**Blocking Issues:**\n"
            for issue in review_result["blocking_issues"]:
                comment += f"- {issue}\n"
            comment += "\n"
        
        if review_result.get("minor_issues"):
            comment += "**Minor Issues:**\n"
            for issue in review_result["minor_issues"]:
                comment += f"- {issue}\n"
        
        self.add_comment(story, comment, comment_type="decision")
        
        # Send back to dev
        self.update_story_status(story, StoryStatus.DEV)
        self.emit("returned", story,
                  f"QA rejected (attempt {rejection_count}), back to dev: {story.title}")
        
        self.log_action(
            action="qa_reject",
            story=story,
            output=review_result,
            decisions=["rejected"],
        )
        
        self.logger.warning(f"Story #{story.id} failed QA, sent back to dev")


def main():
    """Run the QA agent."""
    agent = QAAgent()
    try:
        agent.run()
    finally:
        agent.close()


if __name__ == "__main__":
    main()
