# Security Guidelines

## Mandatory Security Checks

**Before ANY commit or PR approval, the following MUST be verified:**

### Checklist

- [ ] No hardcoded secrets (API keys, passwords, tokens, private keys)
- [ ] All user inputs validated at system boundaries
- [ ] SQL injection prevention (parameterized queries, no string concatenation)
- [ ] XSS prevention (sanitized HTML, encoded output)
- [ ] CSRF protection enabled on all state-changing endpoints
- [ ] Authentication/authorization verified on protected routes
- [ ] Rate limiting on all public endpoints
- [ ] Error messages don't leak sensitive data (stack traces, keys, etc.)
- [ ] HTTPS enforced in production (no mixed content)
- [ ] Sensitive data encrypted at rest

## Secret Management

### Rules

- **NEVER** hardcode secrets in source code
- **ALWAYS** use environment variables or secret manager
- Validate that required secrets are present at startup
- Rotate any secrets that may have been exposed immediately
- Never commit `.env` or credentials files

### Examples

```python
# ❌ BAD - Hardcoded secret
API_KEY = "sk-proj-abc123def456"

# ✅ GOOD - Environment variable
import os
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY environment variable not set")
```

### Common Secret Patterns to Avoid

- API keys (Stripe, OpenAI, Anthropic, etc.)
- Database passwords
- JWT secret keys
- AWS/Cloud access keys
- Private keys (SSH, SSL/TLS)
- OAuth tokens

## Input Validation

### Rules

- Validate all user input at system boundaries (API endpoints, webhooks, etc.)
- Use schema-based validation (Pydantic, Zod, etc.)
- Fail fast with clear, user-friendly error messages
- Never trust external data (headers, query params, body)

### Examples

```python
# ❌ BAD - No validation
def create_user(request):
    data = request.json()
    User.objects.create(email=data["email"])

# ✅ GOOD - Schema validation
from pydantic import BaseModel, EmailStr, Field

class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)

def create_user(request):
    try:
        data = CreateUserRequest(**request.json())
    except ValidationError as e:
        raise BadRequestError(str(e))
    User.objects.create(email=data.email)
```

## SQL Injection Prevention

### Rules

- **ALWAYS** use parameterized queries
- **NEVER** concatenate user input into SQL strings
- Use ORM when possible (SQLAlchemy, Django ORM, etc.)

### Examples

```python
# ❌ BAD - SQL injection vulnerable
query = f"SELECT * FROM users WHERE email = '{email}'"

# ✅ GOOD - Parameterized query
query = "SELECT * FROM users WHERE email = %s"
cursor.execute(query, (email,))

# ✅ GOOD - ORM (best)
users = User.objects.filter(email=email)
```

## XSS Prevention

### Rules

- Sanitize all HTML output from user input
- Encode special characters in templates
- Use Content Security Policy (CSP) headers
- Avoid `innerHTML` with user content

### Examples

```python
# ❌ BAD - XSS vulnerable
def render_comment(comment_text):
    return f"<div>{comment_text}</div>"

# ✅ GOOD - Sanitized output
import html
def render_comment(comment_text):
    return f"<div>{html.escape(comment_text)}</div>"
```

## CSRF Protection

### Rules

- Enable CSRF tokens on all state-changing endpoints
- Verify token on POST/PUT/DELETE/PATCH requests
- Use framework's built-in CSRF protection

### Examples

```python
# Flask example
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)

# FastAPI example
from fastapi_csrf_protect import CsrfProtect
csrf_protect = CsrfProtect(secret="your-secret-key")
```

## Rate Limiting

### Rules

- Apply rate limits to all public endpoints
- Use different limits for authenticated vs anonymous users
- Implement backoff strategy
- Log rate limit violations

### Recommended Limits

| Endpoint Type | Limit | Window |
|---------------|--------|---------|
| Authentication (login) | 5 requests | 15 minutes |
| Public API | 100 requests | 1 hour |
| Authenticated API | 1000 requests | 1 hour |
| Webhooks | 10 requests | 1 minute |

## Error Messages

### Rules

- Never leak sensitive data in error messages
- Log detailed errors server-side
- Provide user-friendly messages client-side
- Don't include: stack traces, keys, paths, internal details

### Examples

```python
# ❌ BAD - Leaks sensitive info
try:
    result = db.query(...)
except DatabaseError as e:
    return error(f"Database connection failed to {db.host}: {e}")

# ✅ GOOD - User-friendly, logs details
try:
    result = db.query(...)
except DatabaseError as e:
    logger.error(f"Database error: {e}", exc_info=True)
    return error("Unable to complete request. Please try again later.")
```

## Authentication & Authorization

### Rules

- Always verify authentication on protected routes
- Check authorization (user has permission)
- Use JWT with proper expiration
- Implement refresh token flow
- Invalidate tokens on password change/logout

## Encryption

### Rules

- Encrypt sensitive data at rest (passwords, PII, tokens)
- Use HTTPS in production (TLS 1.2+)
- Store only hashed passwords (bcrypt, argon2, scrypt)
- Use strong encryption algorithms (AES-256, ChaCha20)

### Password Hashing

```python
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())
```

## API Security Headers

### Required Headers

```python
# Apply these headers to all responses
security_headers = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Content-Security-Policy": "default-src 'self'",
}
```

## Security Review Protocol

### Before ANY Story Approval

Architect agent MUST verify:

1. No hardcoded secrets (regex scan)
2. All inputs validated (schema check)
3. SQL injection protected (parameterized query check)
4. XSS protected (output encoding check)
5. CSRF enabled (framework config check)
6. Auth/z verified (protected routes check)
7. Rate limiting configured (endpoint limits check)
8. Error messages don't leak (review error handling)
9. HTTPS enforced (production config check)
10. Sensitive data encrypted (database schema check)

If ANY CRITICAL or HIGH security issue is found, REJECT story.

## Common Security Pitfalls

- Hardcoding secrets in code or comments
- Using `eval()` or `exec()` with user input
- Trusting client-side data
- Forgetting to validate after type casting
- Ignoring return values from security functions
- Rolling own crypto (use libraries instead)
- Weak password hashing (MD5, SHA1)
- Storing passwords in plain text

## Security Testing

### Required Tests

- [ ] Unit tests for input validation
- [ ] Unit tests for authentication/authorization
- [ ] Integration tests for rate limiting
- [ ] Security scan tools (OWASP ZAP, Burp Suite)
- [ ] Dependency vulnerability scans (pip-audit, Snyk)

---

## Severity Levels

| Level | Action |
|--------|--------|
| **CRITICAL** | Block release, fix immediately, rotate secrets |
| **HIGH** | Block release, fix before next deployment |
| **MEDIUM** | Fix within 1 week, monitor |
| **LOW** | Fix in next sprint |

---

**Remember:** Security is not optional. Every commit, every PR, every story must pass these checks.
