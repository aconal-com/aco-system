#!/usr/bin/env python3
"""
Manually create tasks and update story to ready-architect
"""
import sys
sys.path.insert(0, '/home/ubuntu/.openclaw/workspace/aco-system')

from config.settings import get_settings
from core.database import init_database, get_session, Story, Task, TaskStatus, StoryStatus
from datetime import datetime

print("="*70)
print("  CREATING TASKS MANUALLY")
print("="*70)
print()

# Initialize database
settings = get_settings()
init_database(settings.DATABASE_URL)
session = get_session()
print("✓ Database initialized\n")

# Get story
story = session.query(Story).filter(Story.id == 1).first()

if not story:
    print("❌ Story #1 not found")
    sys.exit(1)

print(f"✓ Found Story #1: {story.title}")
print(f"✓ Current Status: {story.status.value}")
print()

# Create tasks
tasks_to_create = [
    {
        "title": "Set up Flutter project structure",
        "description": "Initialize Flutter project, configure dependencies, set up folder structure for lib/, test/, android/, ios/",
        "estimate_hours": 4,
        "dependencies": [],
        "technical_notes": "Use Flutter CLI, follow pub.dev conventions"
    },
    {
        "title": "Design Firebase authentication flow",
        "description": "Configure Firebase Auth for email/password and Google sign-in, set up user profile schema",
        "estimate_hours": 6,
        "dependencies": [1],
        "technical_notes": "Use firebase_auth package, handle auth state changes"
    },
    {
        "title": "Create FastAPI backend structure",
        "description": "Set up FastAPI project, configure Pydantic models, CORS, middleware, health endpoint",
        "estimate_hours": 5,
        "dependencies": [],
        "technical_notes": "Use FastAPI, uvicorn, follow project structure best practices"
    },
    {
        "title": "Implement resume upload endpoint",
        "description": "Create POST /api/resume endpoint, validate PDF/DOCX files, extract text content",
        "estimate_hours": 8,
        "dependencies": [3],
        "technical_notes": "Use python-multipart for file uploads, PyPDF2 or docx2txt for parsing"
    },
    {
        "title": "Build resume parsing service",
        "description": "Extract skills, experience, education from resume text, store in MySQL database",
        "estimate_hours": 12,
        "dependencies": [4],
        "technical_notes": "Use NLP or regex patterns, normalize skill data"
    },
    {
        "title": "Implement job description input",
        "description": "Create UI for pasting JD or entering URL, extract key requirements and skills",
        "estimate_hours": 6,
        "dependencies": [],
        "technical_notes": "Flutter TextField, auto-extract keywords"
    },
    {
        "title": "Implement company research API",
        "description": "Research company based on JD, extract: company name, size, tech stack",
        "estimate_hours": 8,
        "dependencies": [],
        "technical_notes": "Use web_search tool, extract company info"
    },
    {
        "title": "Build voice interview UI",
        "description": "Implement voice call interface, connect to ChatGPT Realtime API",
        "estimate_hours": 12,
        "dependencies": [1],
        "technical_notes": "Flutter audio streaming, WebSocket connection"
    },
    {
        "title": "Integrate OpenRouter for AI questions",
        "description": "Integrate OpenRouter API, generate questions based on resume + JD",
        "estimate_hours": 10,
        "dependencies": [5, 6, 7],
        "technical_notes": "Use OpenRouter minimax/minimax-m2.5 model"
    },
    {
        "title": "Implement feedback system",
        "description": "Score interviews, generate feedback reports, provide improvement suggestions",
        "estimate_hours": 8,
        "dependencies": [9],
        "technical_notes": "Scoring algorithm, feedback templates"
    },
    {
        "title": "Testing & deployment",
        "description": "Write unit tests, integration tests, deploy to AWS",
        "estimate_hours": 10,
        "dependencies": [10],
        "technical_notes": "pytest, AWS EC2 deployment"
    }
]

print(f"Creating {len(tasks_to_create)} tasks...\n")

for i, task_data in enumerate(tasks_to_create, 1):
    task = Task(
        story_id=story.id,
        title=task_data["title"],
        description=task_data["description"],
        estimate_hours=task_data["estimate_hours"],
        dependencies=",".join(map(str, task_data["dependencies"])) if task_data["dependencies"] else None,
        output_json={"technical_notes": task_data.get("technical_notes", "")},
        status=TaskStatus.TODO,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    session.add(task)
    print(f"✓ Task {i}: {task_data['title']} ({task_data['estimate_hours']} hours)")

session.commit()

print(f"\n✓ Created {len(tasks_to_create)} tasks for Story #1")
print()

# Update story status to ready-architect
story.status = StoryStatus.READY_ARCHITECT
story.updated_at = datetime.utcnow()
story.assigned_agent = None

session.commit()

print(f"✓ Updated story status to: {StoryStatus.READY_ARCHITECT.value}")
print()

# Calculate total hours
total_hours = sum(t["estimate_hours"] for t in tasks_to_create)
print("="*70)
print(f"  SUMMARY")
print("="*70)
print(f"\nTotal Tasks: {len(tasks_to_create)}")
print(f"Total Estimate: {total_hours} hours (~{total_hours//8} days)")
print(f"Story Status: {story.status.value}")
print()
print("Next: Run architect agent to review and approve")
print("  python3 run_architect.py")
print()

session.close()
