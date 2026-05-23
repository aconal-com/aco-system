# Changelog

All notable changes to ACO System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.0] - 2025-03-30

### Added
- **Phase 1: Agent Markdown Prompts & Model Tiering** — Agents defined in `agent_prompts/*.md` with YAML frontmatter; Opus for complex reasoning, Sonnet for implementation, None for human routing
- **Phase 2: Rules Injection** — `rules/common/` with mandatory standards (security, coding-standards, git-workflow, testing) injected into agent context
- **Phase 3: Validation Hooks** — Pre/post transition validation via deterministic JSON configs (no LLM for hard gates like secret detection and schema compliance)
- **Phase 4: Skills & Contexts** — Domain knowledge in `skills/`, project context in `contexts/`, and context trimming for long-running stories
- **Six-Agent Pipeline** — PM → Planner → Architect → Dev → QA → Human Reviewer
- **Next.js Dashboard** — Real-time Kanban board with live agent status, story timelines, task details, and event feed
- **GitHub Integration** — Stories sync with GitHub issues and pull requests
- **Multi-LLM Support** — OpenAI, Anthropic, xAI, and OpenRouter providers configurable via environment variables
- **PostgreSQL + SQLite** — Works with SQLite for local dev, PostgreSQL for production

### Removed
- Experimental test scripts (moved to `experiments/` or deleted prior to open source release)
- Legacy `.venv` virtual environment directory

[0.1.0]: https://github.com/aniketkarne/aco-system/releases/tag/v0.1.0
