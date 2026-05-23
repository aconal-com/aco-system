"""
Planner Agent (aco-planner)

Responsibilities:
- Take stories from PM and break them into detailed tasks
- Use MCP to generate screen designs for UI tasks
- Estimate effort for each task
- Identify dependencies between tasks
- Create task definitions that reference generated screens

Workflow:
1. Pick up story with status "ready-planner"
2. Read full context from PM (including research findings)
3. Prompt MCP to generate screens for mobile apps
4. Break down into atomic, testable tasks
5. Each task references a screen ID (if applicable)
6. Mark story as "ready-architect"
"""
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from agents.base_agent import BaseAgent
from core.database import Story, Task, StoryStatus, TaskStatus
from integrations.llm_client import get_client


class PlannerAgent(BaseAgent):
    """Planner agent that breaks down stories into tasks and generates screens via MCP."""

    AGENT_NAME = "aco-planner"
    HANDLES_STATUSES = [StoryStatus.READY_PLANNER]

    def process_story(self, story: Story):
        """
        Break down a story into detailed tasks with screen generation.
        """
        try:
            self.logger.info(f"Planning Story #{story.id}: {story.title}")

            # Step 1: Prepare context for LLM (messages list for LLM)
            llm_messages = super().build_llm_context(story)

            # Step 2: Use LLM to plan tasks and generate screens
            llm_client = get_client(self.AGENT_NAME)
            plan_result = self._get_plan_from_llm(llm_client, story)

            # Step 3: Generate screens via MCP if mobile app
            screens = []
            story_context = story.context_json or {}

            if self._is_mobile_app(story):
                screens = self._generate_screens_via_mcp(story, {}, plan_result)
                story_context["screens_generated"] = True

            # Step 4: Create tasks in database
            created_tasks = self._create_tasks(story, plan_result["tasks"], screens)

            # Step 5: Update story context and status
            story.context_json = story.context_json or {}
            story.context_json.update(story_context)
            story.context_json["planner_summary"] = {
                "planned_at": datetime.utcnow().isoformat(),
                "total_tasks": len(created_tasks),
                "total_estimate_hours": sum(t.estimate_hours or 0 for t in created_tasks),
                "screens_generated": len(screens),
            }

            self.db.commit()

            # Step 6: Hand off to architect
            # Validation is automatic in BaseAgent.update_story_status()
            self.update_story_status(story, StoryStatus.READY_ARCHITECT)

            # Add summary comment
            self.add_comment(
                story,
                f"## 📋 Planning Complete\n\n{self._format_plan_summary(created_tasks, screens)}",
                comment_type="note",
            )

            # Create GitHub issues for each task
            try:
                task_issues = self.github_sync.create_task_issues(story, created_tasks)
                if task_issues:
                    issue_lines = "\n".join(
                        f"#{created_tasks[i].id}: {created_tasks[i].title} → GitHub #{task_issues[i]}"
                        for i in range(len(task_issues))
                    )
                    self.add_comment(
                        story,
                        f"## 🔗 Task GitHub Issues\n\n{issue_lines}",
                        comment_type="note",
                    )
                    self.logger.info(f"Created {len(task_issues)} GitHub issues for tasks")
            except Exception as e:
                self.logger.warning(f"Failed to create task GitHub issues: {e}")

            self.log_action(
                action="plan_story",
                story=story,
                output={
                    "tasks_created": len(created_tasks),
                    "screens_generated": len(screens),
                    "total_estimate_hours": story.context_json.get("planner_summary", {}).get("total_estimate_hours", 0),
                },
            )

        except Exception as e:
            self.logger.error(f"Error planning story: {e}", exc_info=True)
            self.release_story(story)
            raise

    def _is_mobile_app(self, story: Story) -> bool:
        """Check if this is a mobile app story that needs screens."""
        description = (story.description or "").lower()
        title = (story.title or "").lower()

        mobile_keywords = [
            "flutter", "mobile", "app", "ios", "android",
            "ui", "screen", "interface", "user experience",
            "design", "wireframe", "mockup"
        ]

        return any(keyword in description or keyword in title for keyword in mobile_keywords)

    def _generate_screens_via_mcp(self, story: Story, context: Dict, plan_result: Dict) -> List[Dict]:
        """
        Generate screens via MCP server.
        Returns list of screen objects with IDs.
        """
        self.logger.info(f"Generating screens via MCP for story #{story.id}")

        # For now, mock screen generation
        # In production, this would call the MCP tool
        screens = []

        # Extract screen types from tasks
        for task in plan_result["tasks"]:
            screen_type = self._identify_screen_type(task, story)

            if screen_type:
                screen_id = f"screen_{len(screens) + 1}"
                screen = {
                    "id": screen_id,
                    "type": screen_type,
                    "title": task["title"],
                    "description": task["description"],
                    "elements": self._generate_screen_elements(screen_type, task, story),
                }
                screens.append(screen)
                # Attach screen ID to task
                task["screen_id"] = screen_id

        return screens

    def _identify_screen_type(self, task: Dict, story: Story) -> Optional[str]:
        """Identify what type of screen this task represents."""
        task_title_lower = task["title"].lower()
        task_desc_lower = (task.get("description", "") or "").lower()

        screen_types = {
            "onboarding": ["onboarding", "login", "sign", "register", "welcome"],
            "main": ["home", "dashboard", "main", "feed", "list"],
            "interview": ["interview", "call", "record", "voice", "question", "answer"],
            "profile": ["profile", "settings", "account", "preferences", "my account"],
            "resume": ["resume", "upload", "document", "file", "cv"],
            "job": ["job", "description", "position", "application", "apply"],
            "history": ["history", "interviews", "past", "completed", "saved"],
            "subscription": ["subscription", "payment", "plan", "pricing", "upgrade"],
            "feedback": ["feedback", "report", "result", "score", "rating"],
        }

        for screen_type, keywords in screen_types.items():
            if any(kw in task_title_lower or kw in task_desc_lower for kw in keywords):
                return screen_type

        return None

    def _generate_screen_elements(self, screen_type: str, task: Dict, story: Story) -> List[Dict]:
        """Generate UI elements for a screen type."""
        elements = []

        if screen_type == "onboarding":
            elements = [
                {"type": "logo", "label": "App Logo"},
                {"type": "title", "label": "Welcome to CarInterview"},
                {"type": "button", "label": "Sign In", "action": "login"},
                {"type": "button", "label": "Create Account", "action": "register"},
                {"type": "input", "label": "Email"},
                {"type": "input", "label": "Password", "secure": True},
            ]

        elif screen_type == "main":
            elements = [
                {"type": "card", "label": "Interviews Available"},
                {"type": "button", "label": "+ New Interview", "action": "create_interview"},
                {"type": "button", "label": "View History"},
            ]

        elif screen_type == "interview":
            elements = [
                {"type": "avatar", "label": "AI Interviewer"},
                {"type": "progress", "label": "Interview Progress", "current": "0"},
                {"type": "text", "label": "Question", "content": "Tell me about yourself..."},
                {"type": "button", "label": "Answer"},
                {"type": "mic", "label": "Microphone", "action": "toggle_mic"},
            ]

        elif screen_type == "profile":
            elements = [
                {"type": "avatar", "label": "User"},
                {"type": "input", "label": "Name"},
                {"type": "input", "label": "Email"},
                {"type": "toggle", "label": "Subscription"},
            ]

        return elements

    def _build_planning_context(self, story: Story) -> Dict:
        """Build context for LLM planning."""
        return {
            "story_id": story.id,
            "title": story.title,
            "description": story.description,
            "acceptance_criteria": story.acceptance_criteria,
            "context": story.context_json,
            "comments": [
                {"author": c.author, "content": c.content, "type": c.comment_type}
                for c in story.comments
            ],
            "is_mobile_app": self._is_mobile_app(story),
        }

    def _get_plan_from_llm(self, llm, story: Story) -> Dict:
        """Use LLM to break down story into tasks."""
        system_prompt = """You are an expert technical planner for software development teams.
Your output is MACHINE-READABLE and EXECUTION-READY.

## YOUR OUTPUT CONTRACT (STRICT — 8 required fields per task)

Every task MUST have ALL of these fields:

1. **title**: Clear title WITH [implement] or [test] prefix. Example: "[implement] Create exchange rate API client"
2. **description**: Full description of what this task does and how
3. **file_path**: Exact file path to create/modify. Example: "services/exchange_rates.py"
4. **function_signature**: Complete function signature. Example: "def fetch_rate(from: str, to: str) -> Optional[float]:"  (use "N/A" for test files and pure infra)
5. **dependencies**: List of task IDs this depends on (can be empty list [])
6. **acceptance_criteria**: Numbered list of specific, testable criteria. Each maps to a test case. Format: "1. ... 2. ... 3. ..."
7. **test_strategy**: Framework + mock strategy. Example: "pytest.mark.parametrize with mocked httpx responses"
8. **estimate_hours**: 1-16 hours
9. **technical_notes**: Implementation decisions, library choices, patterns to follow

## WORKED EXAMPLE

**BAD output (vague):**
{
  "title": "Implement API client",
  "description": "Create a function to fetch exchange rates",
  "estimate_hours": 3
}
❌ Developer must guess: function signature? args? return type? errors? tests?

**GOOD output (explicit):**
{
  "title": "[implement] Create exchange rate API client",
  "description": "Create fetch_exchange_rate() using httpx against exchangerate.host. Handle 4xx/5xx with ExchangeRateError. Validate currency codes are 3 uppercase letters.",
  "file_path": "services/exchange_rates.py",
  "function_signature": "def fetch_exchange_rate(from_currency: str, to_currency: str, api_key: str) -> Union[float, None]:",
  "dependencies": [2],
  "acceptance_criteria": "1. Function takes from_currency(str), to_currency(str), api_key(str). 2. GET https://api.exchangerate.host/latest?base={from}&symbols={to}. 3. Returns float rate or None if currencies identical. 4. Raises ExchangeRateError on HTTP 4xx/5xx. 5. Raises ValueError if currency code not 3 uppercase letters. 6. Timeout=10s, retry once on 429.",
  "test_strategy": "pytest.mark.parametrize: [(USD,EUR), (EUR,GBP), (JPY,INR)]. Mock httpx.Client.post to return {\"rates\": {\"EUR\": 0.92}}. Test: identical currencies return 1.0, invalid code raises ValueError, HTTP error raises ExchangeRateError, timeout raises ExchangeRateError.",
  "technical_notes": "Use httpx (not requests). Base URL from settings.EXCHANGE_RATE_API_URL.",
  "estimate_hours": 3
}

**PAIRED TEST TASK (always follows [implement] task touching logic):**
{
  "title": "[test] Write unit tests for exchange rate API client",
  "description": "Write pytest unit tests covering all acceptance criteria from task #N.",
  "file_path": "tests/test_exchange_rates.py",
  "function_signature": "N/A (test file)",
  "dependencies": [N],
  "acceptance_criteria": "1. All acceptance criteria from task #N have corresponding test cases. 2. Parametrized tests cover [USD,EUR], [EUR,GBP], [JPY,INR]. 3. Mock covers happy path, timeout, HTTP 429, HTTP 500.",
  "test_strategy": "pytest.mark.parametrize with 3 currency pairs. Use unittest.mock to patch httpx.Client.post. Use @pytest.mark.timeout(10) for timeout tests.",
  "technical_notes": "Tests import from services.exchange_rates.",
  "estimate_hours": 2
}

## IMPLEMENTATION + TEST PAIRS (MANDATORY)

Every [implement] task that touches logic MUST be followed by a paired [test] task.
Infrastructure tasks (README, requirements.txt, .env config) do NOT need paired tests.

## TECH STACK
Check in order: 1) projects/{story_id}/TECH.md → 2) Story tech_stack field → 3) Infer from description.
Do NOT invent technology choices not specified.

## OUTPUT FORMAT
{
  "tasks": [ ... all task objects with all 9 required fields ... ],
  "total_estimate_hours": N,
  "critical_path": [task_id_1, task_id_3, task_id_5],
  "risks": [{"risk": "...", "probability": "medium", "impact": "high", "mitigation": "..."}],
  "architecture_diagram": "ASCII diagram",
  "data_flow_diagram": "ASCII diagram",
  "state_machine_diagram": "ASCII diagram"
}"""


        user_prompt = f"""Break down this story into detailed, executable tasks:

**Story:** {story.title}
**Description:** {story.description}
**Acceptance Criteria:** {json.dumps(story.acceptance_criteria or [], indent=2)}
**PM Research Findings:** {json.dumps(story.context_json.get('pm_research_findings', []) if story.context_json else [], indent=2)}
**Tech Stack:** {json.dumps(story.context_json.get('tech_stack', 'infer from description'), indent=2)}


Each task must have all 9 fields: title([implement]/[test] prefix), description, file_path, function_signature, dependencies, acceptance_criteria (numbered), test_strategy, technical_notes, estimate_hours.

Every [implement] task that touches logic MUST be followed by its paired [test] task.
Return ONLY valid JSON."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = llm.chat(messages, temperature=0.3)

        # Handle None or empty response
        if not response:
            self.logger.warning("LLM returned empty response, using default plan")
            return {
                "tasks": [{
                    "title": f"Implement {story.title}",
                    "description": story.description,
                    "estimate_hours": 8,
                    "dependencies": [],
                }]
            }

        try:
            from core.json_utils import extract_json
            # Find JSON in response using brace-counting extraction
            parsed = extract_json(response)
            if parsed is not None:
                return parsed
            raise ValueError("extract_json returned None")
        except Exception as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {e}")
            # Return empty tasks — let human reviewer decide, don't auto-generate bad breakdown
            return {"tasks": [], "total_estimate_hours": 0}

    def _create_tasks(self, story: Story, tasks_data: List[Dict], screens: List[Dict]) -> List[Task]:
        """Create task records in database."""
        created_tasks = []

        for i, task_data in enumerate(tasks_data, 1):
            task = Task(
                story_id=story.id,
                title=task_data.get("title", f"Task {i}"),
                description=task_data.get("description", ""),
                estimate_hours=task_data.get("estimate_hours"),
                dependencies=task_data.get("dependencies", []),
                status=TaskStatus.TODO,
                output_json={
                    # Core implementation spec (new fields)
                    "file_path": task_data.get("file_path", ""),
                    "function_signature": task_data.get("function_signature", ""),
                    "acceptance_criteria": task_data.get("acceptance_criteria", ""),
                    "test_strategy": task_data.get("test_strategy", ""),
                    # Screen generation (mobile)
                    "screen_id": task_data.get("screen_id"),
                    "technical_notes": task_data.get("technical_notes", ""),
                    "screen_elements": None,  # Will populate from screens
                    # Metadata
                    "impl_or_test": "[implement]" if "[implement]" in task_data.get("title", "") else "[test]" if "[test]" in task_data.get("title", "") else "[implement]",
                },
            )
            self.db.add(task)
            created_tasks.append(task)


        # Link tasks to screens
        for screen in screens:
            screen_id = screen["id"]
            matching_tasks = [t for t in created_tasks if t.output_json.get("screen_id") == screen_id]

            if matching_tasks:
                for task in matching_tasks:
                    if not task.output_json:
                        task.output_json = {}
                    task.output_json["screen_elements"] = screen.get("elements", [])

        self.db.commit()

        # Refresh to get IDs
        for task in created_tasks:
            self.db.refresh(task)

        return created_tasks

    def _format_plan_summary(self, tasks: List[Task], screens: List[Dict]) -> str:
        """Format plan summary as readable text."""
        lines = [
            f"**Tasks Created:** {len(tasks)}",
            f"**Total Estimate:** {sum(t.estimate_hours or 0 for t in tasks)} hours",
        ]

        if screens:
            lines.append(f"**Screens Generated:** {len(screens)}")
            for i, screen in enumerate(screens, 1):
                lines.append(f"  {i}. {screen['type']}: {screen['title']} ({len(screen.get('elements', []))} elements)")

        return "\n".join(lines)


def main():
    """Run planner agent."""
    agent = PlannerAgent()
    try:
        agent.run()
    finally:
        agent.close()


if __name__ == "__main__":
    main()
