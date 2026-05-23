# ACO System - Project Context

## Project Overview

ACO (Autonomous Company Operating System) is a multi-agent development team framework. Six specialized agents collaborate through a shared database to take software projects from requirements to shipped code.

## Tech Stack

- **Language**: Python 3.11+
- **Backend**: FastAPI
- **Database**: PostgreSQL (production) / SQLite (development)
- **LLM**: Anthropic Claude (Opus, Sonnet, Haiku) or OpenAI / xAI / OpenRouter
- **GitHub**: PyGithub for repository operations
- **Frontend**: Next.js 15 + Tailwind CSS
- **Task Queue**: Celery + Redis (optional)

## Architecture

### Multi-Agent System

Six specialized agents collaborate through a shared database:

| Agent | Role | Model |
|-------|------|-------|
| aco-pm | Requirements, user stories, web research | Sonnet |
| aco-planner | Task breakdown, estimation, dependencies | Opus |
| aco-architect | Technical validation, security, approval | Opus |
| aco-dev | Implementation, best practices | Sonnet |
| aco-qa | Testing, code review | Sonnet |
| aco-human | Human review, routing, notifications | None (no LLM) |

### Workflow Pipeline

```
pm-review → ready-planner → ready-architect → approved → dev → qa → human-review → done
```

### Data Flow

1. **User Input**: GitHub issue or dashboard message
2. **PM Agent**: Research, gather requirements, create user story
3. **Planner Agent**: Break down into atomic tasks, estimate dependencies
4. **Architect Agent**: Technical review, security validation, approve/reject
5. **Dev Agent**: Implement, create PRs, write tests
6. **QA Agent**: Review, test, validate acceptance criteria
7. **Human Agent**: Final review, approve, mark done

## Key Features

### Agent Prompts (Phase 1)

- Markdown files with YAML frontmatter
- Tool scoping per agent
- Model tiering (Opus for complex, Sonnet for implementation)
- Easy to edit without code changes

### Rules Injection (Phase 2)

- `rules/common/` with security, coding-standards, git-workflow, testing
- Agents get relevant rules injected into context
- Rules are mandatory (must follow)
- Architect MUST review security before approval

### Validation Hooks (Phase 3)

- `hooks/` with pre/post transition validation
- Deterministic checks (no LLM for hard gates)
- Security regex patterns for secret detection
- Pre-architect-approval is CRITICAL gate

### Skills & Contexts (Phase 4)

- `skills/` for deep domain knowledge (Python, FastAPI patterns)
- `contexts/` for project-specific information
- Context trimming for long-running stories

## Design Decisions

### Why Python?

- Mature ecosystem (FastAPI, SQLAlchemy, Pydantic)
- Type hints support
- Async/await for I/O operations
- Excellent documentation

### Why Multi-Agent vs Single?

- Specialization: Each agent has focused role
- Parallel processing: Multiple agents can work simultaneously
- Audit trail: Clear responsibility per action
- Scalability: Easy to add new agents

### Why Deterministic Validation?

- Prevent LLM hallucinations on security checks
- Reliable, repeatable validation
- Faster than LLM calls for simple checks
- LLM only for advisory warnings

## Current State

### Completed

- ✅ Phase 1: Agent markdown prompts and model tiering
- ✅ Phase 2: Rules injection and tool scoping
- ✅ Phase 3: Validation hooks with deterministic checks
- ✅ Phase 4: Skills and contexts

### Next Steps

- Context trimming implementation
- Enhanced audit trail
- Integration testing
- Documentation updates

## License

MIT License — see LICENSE file in repository root.
