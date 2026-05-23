# Coding Standards

## Core Principles

### 1. Immutability

**CRITICAL**: Always create new objects, never mutate existing ones.

This makes code predictable, easier to debug, and avoids side effects.

#### Examples

```python
# ❌ BAD - Mutating
def update_user(user, new_email):
    user.email = new_email
    return user

# ✅ GOOD - Immutable
def update_user(user, new_email):
    return {**user, "email": new_email}  # Dict copy

# Or with dataclasses
from dataclasses import dataclass, replace

@dataclass(frozen=True)
class User:
    email: str
    name: str

def update_user(user, new_email):
    return replace(user, email=new_email)
```

#### When to Use Immutability

- Function parameters (never modify inputs)
- Return values (always new objects)
- State updates (create new state, don't mutate)
- Configuration (never modify global config)

#### Exceptions

Only mutate when:
- Performance is critical (and benchmarks show improvement)
- Working with external libraries that require mutation
- Operating on in-place data structures (lists, dicts in loops)

### 2. File Organization

#### Principle

**Many small files over few large ones.**

#### Guidelines

| Aspect | Recommendation |
|---------|---------------|
| File size | 200-400 lines typical, 800 max |
| Lines per function | < 50 lines |
| Nesting depth | < 4 levels |
| Cohesion | High (related code together) |
| Coupling | Low (minimal dependencies) |

#### Directory Structure

```
# ✅ GOOD - Organized by feature/domain
features/
  auth/
    auth_service.py
    auth_routes.py
    auth_models.py
    auth_tests.py
  payments/
    payment_service.py
    payment_routes.py
    payment_models.py
    payment_tests.py

# ❌ BAD - Organized by type (low cohesion)
models/
  auth.py
  payment.py
routes/
  auth_routes.py
  payment_routes.py
services/
  auth_service.py
  payment_service.py
```

#### File Naming

- Use snake_case: `user_service.py`, `payment_routes.py`
- One class/module per file (usually)
- Test files: `test_user_service.py`, `test_payment_routes.py`

### 3. Error Handling

#### Guidelines

- Handle errors at every level
- Provide user-friendly messages in UI code
- Log detailed context server-side
- Never silently swallow errors

#### Examples

```python
# ❌ BAD - Silent error
def get_user(user_id):
    try:
        return User.query.get(user_id)
    except Exception:
        pass  # User gets None, no clue why

# ✅ GOOD - Proper handling
def get_user(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            raise UserNotFoundError(user_id)
        return user
    except DatabaseError as e:
        logger.error(f"Database error getting user {user_id}: {e}", exc_info=True)
        raise UserFacingError("Unable to retrieve user. Please try again.")

# UI Code (user-friendly)
def display_user(user_id):
    try:
        user = get_user(user_id)
        return render_user_card(user)
    except UserNotFoundError:
        return render_error("User not found")
    except UserFacingError as e:
        return render_error(str(e))
```

#### Error Types

```python
# Define custom exceptions
class UserFacingError(Exception):
    """Error safe to show to users."""
    pass

class ValidationError(Exception):
    """Input validation error."""
    pass

class DatabaseError(Exception):
    """Database operation error."""
    pass

# Use appropriate exception types
def create_user(data):
    if not data.get("email"):
        raise ValidationError("Email is required")
    try:
        user = User.create(**data)
    except Exception as e:
        logger.error(f"Failed to create user: {e}", exc_info=True)
        raise UserFacingError("Unable to create account. Please try again.")
```

### 4. Input Validation

#### Guidelines

- Validate all user input at system boundaries
- Use schema-based validation
- Fail fast with clear messages
- Never trust external data

#### Examples

```python
# ❌ BAD - No validation
def create_user(request):
    data = request.json()
    User.objects.create(
        email=data["email"],
        password=data["password"]
    )

# ✅ GOOD - Schema validation
from pydantic import BaseModel, EmailStr, Field, constr

class CreateUserRequest(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)

def create_user(request):
    try:
        data = CreateUserRequest(**request.json())
    except ValidationError as e:
        raise BadRequestError(str(e))
    User.objects.create(**data.dict())
```

#### Validation Layers

1. **Schema validation** (Pydantic/Zod): Type checking, constraints
2. **Business logic validation**: Domain rules (e.g., email unique)
3. **Database validation**: Constraints (unique, foreign keys)

### 5. Code Quality

#### Function Design

- **Single Responsibility**: Do one thing well
- **Small**: < 50 lines, ideally < 30
- **Pure**: No side effects when possible
- **Named clearly**: Describe what it does, not how

#### Examples

```python
# ❌ BAD - Does too much
def process_payment(user_id, amount, card_info):
    # Validate card
    # Check balance
    # Charge card
    # Update database
    # Send email
    # Update analytics
    # ...

# ✅ GOOD - Split into focused functions
def validate_card(card_info: dict) -> bool:
    """Validate credit card information."""
    # ...

def check_balance(user_id: int, amount: float) -> bool:
    """Check if user has sufficient balance."""
    # ...

def charge_card(card_info: dict, amount: float) -> dict:
    """Charge credit card via payment processor."""
    # ...

def update_payment_record(user_id: int, payment: dict):
    """Save payment to database."""
    # ...

def send_payment_receipt(user_id: int, payment: dict):
    """Send email receipt to user."""
    # ...

def process_payment(user_id, amount, card_info):
    """Process payment with all steps."""
    if not validate_card(card_info):
        raise InvalidCardError()
    if not check_balance(user_id, amount):
        raise InsufficientFundsError()
    payment = charge_card(card_info, amount)
    update_payment_record(user_id, payment)
    send_payment_receipt(user_id, payment)
    return payment
```

#### Variable Naming

- **Descriptive**: `user_email`, not `e` or `eml`
- **Consistent**: Use same naming style across codebase
- **No abbreviations**: `user_count`, not `usr_cnt`
- **Boolean prefixes**: `is_active`, `has_permission`, `can_edit`

#### Comments

- **Code should be self-documenting**
- Only comment **why**, not **what**
- Delete commented-out code (use git for history)
- Keep comments up to date

```python
# ❌ BAD - Comments say what
# Get user from database
user = User.query.get(user_id)

# Update user email
user.email = new_email

# Save to database
user.save()

# ❌ BAD - Commented code
# def old_function():
#     pass

# ✅ GOOD - Comments explain why
# Use index lookup for O(1) performance instead of iteration
user = user_cache.get(user_id) or User.query.get(user_id)

# Validate email format to prevent SQL injection
# Email validation regex is per RFC 5322
if not re.match(email_regex, email):
    raise ValidationError("Invalid email format")
```

### 6. Type Hints

**Use type hints on all function signatures.**

#### Examples

```python
# ❌ BAD - No type hints
def get_user(user_id):
    return User.query.get(user_id)

# ✅ GOOD - Type hints
from typing import Optional

def get_user(user_id: int) -> Optional[User]:
    """Get user by ID."""
    return User.query.get(user_id)

# With return types for complex data
from typing import List, Dict

def get_users_by_role(role: str) -> List[Dict[str, str]]:
    """Get all users with given role."""
    users = User.query.filter_by(role=role).all()
    return [
        {"id": u.id, "email": u.email}
        for u in users
    ]
```

### 7. Testing

#### Test Structure

- **Arrange**: Set up test data
- **Act**: Call function being tested
- **Assert**: Verify expected behavior

#### Examples

```python
def test_login_success():
    # Arrange
    user = create_user(email="test@example.com", password="password123")
    login_data = {"email": "test@example.com", "password": "password123"}

    # Act
    result = auth_service.login(**login_data)

    # Assert
    assert result["success"] is True
    assert "token" in result
    assert result["user"]["email"] == "test@example.com"
```

#### Test Coverage

- **Minimum 80%** coverage
- 100% for critical paths (auth, payments)
- Test both happy path and edge cases

### 8. Dependencies

#### Guidelines

- Keep dependencies minimal
- Use stable, well-maintained libraries
- Pin versions in production
- Regularly update dependencies
- Review security vulnerabilities

#### Requirements Format

```text
# requirements.txt
fastapi==0.104.1  # Pin exact version for production
pydantic>=2.0,<3.0  # Allow patch updates
sqlalchemy~=2.0  # Tilde allows minor updates
```

## Code Review Checklist

Before submitting code for review:

- [ ] Functions are small (< 50 lines)
- [ ] Files are focused (< 800 lines)
- [ ] No deep nesting (> 4 levels)
- [ ] No code duplication
- [ ] Proper error handling
- [ ] Input validation present
- [ ] Type hints on all functions
- [ ] Tests added/updated
- [ ] No hardcoded values
- [ ] No commented-out code
- [ ] Descriptive names
- [ ] Self-documenting code
- [ ] No unnecessary comments
- [ ] No hardcoded secrets

---

**Remember:** Clean, readable, maintainable code is more valuable than clever, unreadable code.
