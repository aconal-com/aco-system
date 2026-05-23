# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| `main` branch | Yes |

## Reporting a Vulnerability

If you discover a security issue in ACO System, please report it responsibly.

**Do not open a public GitHub Issue for security vulnerabilities.**

Instead, use GitHub's [private vulnerability reporting](https://github.com/aniketkarne/aco-system/security/advisories/new).

Please include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fixes (optional)

## Security Model

ACO System is designed with the following security properties:

- **Deterministic security gates** — The Architect agent cannot approve a story until a regex-based validator confirms no hardcoded secrets are present. No LLM is involved in this check, eliminating hallucination risk.
- **Tool scoping** — Agents only have access to the tools their role requires. A QA agent cannot push code; a PM agent cannot access the LLM client directly.
- **Rules injection** — Security and input validation rules are mandatory constraints loaded into all code-producing agents.
- **Separation of secrets** — Credentials are stored in `.env` (excluded from git) and accessed via environment variables at runtime.

## Best Practices for Deployment

- Never commit `.env` or any file containing live credentials
- Use GitHub Secrets or a secrets manager for CI/CD credentials
- Rotate API tokens regularly
- Run the database with minimal privileges
