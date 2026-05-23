# Git Workflow

## Branch Naming Convention

All branches must follow these patterns:

### Feature Branches

```
feature/story-{id}/{description}
```

Examples:
- `feature/123/user-authentication`
- `feature/456/payment-integration`
- `feature/789/dashboard-redesign`

### Bug Fix Branches

```
fix/story-{id}/{issue-description}
```

Examples:
- `fix/123/login-fails-on-invalid-email`
- `fix/456/payment-timeout-error`

### Chore Branches

```
chore/{task-description}
```

Examples:
- `chore/update-dependencies`
- `chore/refactor-auth-module`

### Hotfix Branches (Production)

```
hotfix/{version}/{issue-description}
```

Examples:
- `hotfix/v1.2.0/security-patch`
- `hotfix/v1.2.1/database-migration-fix`

**Rules:**
- Use kebab-case (lowercase with hyphens)
- Be descriptive (not "fix" but "fix-login-issue")
- Include story ID when available
- Keep under 50 characters if possible

## Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>: <subject>

<body>

<footer>
```

### Types

| Type | When to Use |
|-------|-------------|
| `feat` | New feature or functionality |
| `fix` | Bug fix |
| `refactor` | Code change without functionality change |
| `docs` | Documentation changes |
| `test` | Adding or updating tests |
| `chore` | Maintenance tasks, dependencies, config |
| `perf` | Performance improvements |
| `ci` | CI/CD changes |
| `style` | Code style changes (formatting, etc.) |
| `build` | Build system changes |

### Subject

- Use imperative mood ("add", not "added")
- Lowercase first letter
- No period at end
- 50 characters max

### Body

- Explain **what** and **why** (not how)
- Wrap at 72 characters
- One blank line between subject and body

### Footer

- Reference issues: `Closes #123` or `Fixes #456`
- Breaking changes: `BREAKING CHANGE: description`

### Examples

```bash
# Simple commit
git commit -m "feat: add user authentication"

# Commit with body
git commit -m "feat: add OAuth2 Google login

Users can now sign in with their Google account.
Implements OAuth2 flow using google-auth-library."

# Commit with footer
git commit -m "fix: resolve race condition in task queue

Fixed edge case where concurrent tasks could overwrite each other.
Closes #123"

# Breaking change
git commit -m "feat: redesign API response format

BREAKING CHANGE: API responses now use envelope format:
{
  "success": true,
  "data": {...},
  "error": "..."
}"
```

## Pull Request Process

### Before Creating PR

1. **Update branch** from latest main:
   ```bash
   git checkout main
   git pull
   git checkout feature/123/my-feature
   git rebase main
   ```

2. **Run all tests**:
   ```bash
   pytest
   ```

3. **Check coverage**:
   ```bash
   pytest --cov=src --cov-report=html
   # Must be > 80%
   ```

4. **Run linters**:
   ```bash
   black . --check
   ruff check
   ```

5. **Resolve conflicts** if any

### PR Template

Every PR must include:

```markdown
## Description
[Brief description of what this PR does and why]

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update
- [ ] Refactoring
- [ ] Performance improvement
- [ ] Other

## Changes
- [ ] Change 1
- [ ] Change 2
- [ ] Change 3

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] All tests passing
- [ ] Coverage > 80%

## Related
- Story #123
- Task #456
- Issue #789

## Checklist
- [ ] Code follows project conventions
- [ ] Self-reviewed (removed debug code, TODOs, etc.)
- [ ] No hardcoded secrets
- [ ] Error handling in place
- [ ] Documentation updated (if applicable)
- [ ] Changelog updated (if applicable)
```

### PR Title Format

Follow same format as commits:
- `feat: Add user authentication`
- `fix: Resolve race condition`
- `refactor: Extract auth service`

## Code Review Guidelines

### For Reviewers

- Be constructive and specific
- Focus on code quality, not person
- Provide examples for improvements
- Ask questions if unsure
- Approve only when satisfied

### For Authors

- Respond to all comments
- Fix requested changes
- Update PR (not new commits if possible)
- Push fixes to same branch

### Review Criteria

**Do Not Merge If:**

- Tests failing
- Coverage < 80%
- CRITICAL security issues
- Unresolved blocking comments
- Breaking changes not documented

## Merging

### Merge Strategy

| Branch Type | Merge Type |
|-------------|-------------|
| Feature | Rebase and merge (squash optional) |
| Bug fix | Rebase and merge |
| Hotfix | Rebase and merge, fast-forward if possible |

### Before Merging

1. [ ] All reviewers approved
2. [ ] All checks passing (CI)
3. [ ] No conflicts with main
4. [ ] Story/task linked
5. [ ] Tests passing locally

### After Merging

1. **Delete feature branch** (keep history clean):
   ```bash
   git branch -d feature/123/my-feature
   ```

2. **Notify team** (if applicable)

3. **Update changelog** (if applicable)

## Release Process

### Versioning

Follow [Semantic Versioning](https://semver.org/) (MAJOR.MINOR.PATCH):

- **MAJOR**: Incompatible API changes
- **MINOR**: Backwards-compatible functionality
- **PATCH**: Bug fixes

### Release Checklist

1. [ ] All tests passing
2. [ ] Documentation updated
3. [ ] Changelog updated
4. [ ] Migration scripts created (if needed)
5. [ ] Tag release:
   ```bash
   git tag -a v1.2.3 -m "Release v1.2.3"
   git push origin v1.2.3
   ```

## Git Best Practices

### DO

- Write meaningful commit messages
- Keep commits atomic (one logical change)
- Pull often, push often
- Rebase feature branches before PR
- Delete merged branches
- Use `.gitignore` properly

### DO NOT

- Commit large binary files (use Git LFS if needed)
- Commit sensitive data (keys, passwords)
- Commit build artifacts (node_modules, __pycache__, etc.)
- Squash public history (breaks ability to bisect)
- Force push to shared branches (unless hotfix)
- Merge with `--no-ff` for feature branches (creates unnecessary merge commits)

## Troubleshooting

### Resolve Merge Conflicts

```bash
# 1. Start rebase
git rebase main

# 2. For each conflict:
# Edit files to resolve
git add <resolved-files>
git rebase --continue

# 3. If needed to abort:
git rebase --abort
```

### Undo Last Commit (not pushed)

```bash
# Soft reset (keep changes)
git reset --soft HEAD~1

# Hard reset (discard changes)
git reset --hard HEAD~1
```

### Amend Last Commit (not pushed)

```bash
git add <changed-files>
git commit --amend
```

### Interactive Rebase (clean history)

```bash
git rebase -i HEAD~5
# Reorder, squash, or drop commits as needed
```

---

**Remember:** Clean git history is easier to maintain and debug. Follow these conventions consistently.
