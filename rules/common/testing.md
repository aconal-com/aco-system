# Testing Guidelines

## Coverage Requirements

### Minimum Coverage

- **80% minimum** coverage for all new code
- **100% coverage** for critical paths:
  - Authentication/authorization
  - Payment processing
  - Security-sensitive operations
  - Data validation

### Coverage Reporting

```bash
# Generate coverage report
pytest --cov=src --cov-report=html --cov-report=term

# Check specific module
pytest --cov=src.auth --cov-report=term

# Fail if coverage below threshold
pytest --cov=src --cov-fail-under=80
```

## Test Types

### 1. Unit Tests

Test individual functions, classes, and modules in isolation.

#### When to Write

- Every function/method
- Every utility function
- Every data model
- Every validation rule

#### Example

```python
# test_user_utils.py
def test_validate_email_valid():
    """Test that valid emails pass validation."""
    assert validate_email("user@example.com") is True
    assert validate_email("user.name@example.co.uk") is True

def test_validate_email_invalid():
    """Test that invalid emails fail validation."""
    assert validate_email("invalid") is False
    assert validate_email("invalid@") is False
    assert validate_email("@example.com") is False

def test_validate_email_edge_cases():
    """Test edge cases for email validation."""
    assert validate_email("") is False
    assert validate_email(None) is False
    assert validate_email("user@example.com" * 100) is False
```

#### Guidelines

- **Fast**: Should run in < 1 second per test
- **Isolated**: Don't depend on external services
- **Deterministic**: Same result every time
- **No side effects**: Don't modify database, files, etc.

### 2. Integration Tests

Test interactions between components (APIs, database, etc.).

#### When to Write

- Every API endpoint
- Every database operation
- Every service integration
- Every workflow

#### Example

```python
# test_auth_routes.py
def test_login_success(client, test_user):
    """Test login with valid credentials."""
    response = client.post("/api/auth/login", json={
        "email": test_user.email,
        "password": test_user.password
    })

    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["user"]["email"] == test_user.email

def test_login_invalid_credentials(client, test_user):
    """Test login with invalid credentials."""
    response = client.post("/api/auth/login", json={
        "email": test_user.email,
        "password": "wrongpassword"
    })

    assert response.status_code == 401
    assert "token" not in response.json()

def test_login_missing_fields(client):
    """Test login with missing required fields."""
    response = client.post("/api/auth/login", json={
        "email": test_user.email
    })

    assert response.status_code == 400
    assert "password" in response.json()["errors"]
```

#### Guidelines

- **Use fixtures** for setup data
- **Mock external services** (don't call real APIs)
- **Clean up** after each test
- **Test both success and failure cases**

### 3. End-to-End (E2E) Tests

Test complete user flows from start to finish.

#### When to Write

- Critical user journeys only
- High-risk workflows
- Multi-step processes

#### Examples

```python
# test_e2e_user_registration.py
def test_user_registration_flow(client):
    """Test complete user registration flow."""
    # Step 1: Submit registration form
    response = client.post("/api/auth/register", json={
        "email": "newuser@example.com",
        "password": "Password123!",
        "name": "New User"
    })
    assert response.status_code == 201
    user_id = response.json()["user"]["id"]

    # Step 2: Verify email (if applicable)
    # ...

    # Step 3: Login
    response = client.post("/api/auth/login", json={
        "email": "newuser@example.com",
        "password": "Password123!"
    })
    assert response.status_code == 200
    token = response.json()["token"]

    # Step 4: Access protected endpoint
    response = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "newuser@example.com"
```

#### Guidelines

- **Test real flows**, not just individual endpoints
- **Use real browser** for UI tests (Playwright, Selenium)
- **Test across browsers** if applicable
- **Run in CI pipeline**

## Test-Driven Development (TDD)

### TDD Workflow

1. **Write test first** (RED) — test should FAIL
2. **Write minimal implementation** (GREEN) — test should PASS
3. **Refactor** (IMPROVE) — verify coverage 80%+

### Example

```python
# Step 1: Write test (will fail)
def test_calculate_discount():
    """Test discount calculation for premium users."""
    result = calculate_discount(user_premium=True, amount=100)
    assert result == 20  # 20% discount for premium

# Step 2: Write minimal implementation
def calculate_discount(user_premium: bool, amount: float) -> float:
    if user_premium:
        return amount * 0.2
    return 0

# Step 3: Run test (passes)
# Step 4: Refactor if needed
# Step 5: Add more edge case tests
```

### Benefits of TDD

- **Design better code**: Tests force you to think about API
- **Documentation**: Tests show how code should work
- **Confidence**: Refactor without breaking things
- **Fewer bugs**: Catch issues early

### When to Use TDD

- **Always** for new features
- **Always** for bug fixes (write failing test first)
- **Optional** for trivial code (getters, setters)

## Test Organization

### Directory Structure

```
tests/
  ├── unit/
  │   ├── test_auth_utils.py
  │   ├── test_payment_service.py
  │   └── test_user_models.py
  ├── integration/
  │   ├── test_auth_routes.py
  │   ├── test_payment_routes.py
  │   └── test_database_operations.py
  ├── e2e/
  │   ├── test_user_registration_flow.py
  │   └── test_payment_flow.py
  └── conftest.py  # Shared fixtures and setup
```

### Fixtures

```python
# conftest.py
import pytest
from app.models import User, db

@pytest.fixture
def test_user():
    """Create a test user and clean up after."""
    user = User.create(
        email="test@example.com",
        password="password123",
        name="Test User"
    )
    yield user
    # Cleanup
    user.delete()

@pytest.fixture
def authenticated_client(client, test_user):
    """Create an authenticated test client."""
    token = auth_service.generate_token(test_user)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
```

## Test Data Management

### Guidelines

- **Don't hardcode** test data (use factories/fixtures)
- **Use realistic data** (edge cases, not just happy path)
- **Clean up** after each test
- **Isolate tests** (don't share state)

### Example with Factory

```python
# test_factories.py
class UserFactory:
    """Factory for creating test users."""

    @staticmethod
    def create(email=None, password=None, **kwargs):
        """Create a test user with defaults."""
        return User.create(
            email=email or "test@example.com",
            password=password or "password123",
            name="Test User",
            **kwargs
        )

# In tests
def test_update_user_profile():
    user = UserFactory.create()
    # ... test code ...
```

## Mocking External Services

### Guidelines

- **Mock external APIs** (don't call real services)
- **Mock time-dependent code** (use `freezegun` library)
- **Mock file system** (use `tmp_path` fixture)
- **Mock randomness** (use seed for reproducibility)

### Example

```python
import pytest
from unittest.mock import patch, MagicMock

def test_send_email_on_registration(client, test_user):
    """Test that email is sent on registration."""
    with patch('app.services.email_service.send_email') as mock_send:
        response = client.post("/api/auth/register", json={...})

        assert response.status_code == 201
        assert mock_send.called
        assert mock_send.call_args[0][0] == test_user.email
        assert "Welcome" in mock_send.call_args[0][1]
```

## Error Testing

### Test All Error Paths

```python
def test_login_various_error_cases():
    """Test login error cases."""
    # Invalid email
    response = client.post("/api/auth/login", json={
        "email": "invalid-email",
        "password": "password123"
    })
    assert response.status_code == 400

    # Missing password
    response = client.post("/api/auth/login", json={
        "email": "test@example.com"
    })
    assert response.status_code == 400

    # User not found
    response = client.post("/api/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "password123"
    })
    assert response.status_code == 401

    # Wrong password
    response = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
```

## Performance Testing

### When to Write

- Critical paths (API endpoints, database queries)
- Slow operations (file processing, data imports)
- High-traffic features

### Example

```python
import pytest
import time

def test_login_performance(client, test_user):
    """Test login performance."""
    start_time = time.time()

    response = client.post("/api/auth/login", json={
        "email": test_user.email,
        "password": test_user.password
    })

    duration = time.time() - start_time

    assert response.status_code == 200
    assert duration < 0.5  # Login should complete in < 500ms
```

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -r requirements.txt
      - run: pytest --cov=src --cov-report=xml --cov-report=term
      - uses: codecov/codecov-action@v3
```

### Requirements for Merge

- [ ] All tests passing
- [ ] Coverage > 80%
- [ ] No flaky tests
- [ ] No skipped tests (unless documented)

## Common Testing Pitfalls

### ❌ Bad Practices

1. **Testing implementation, not behavior**:
   ```python
   # Bad: Tests internal implementation
   def test_user_creation():
       assert User.objects.count() == 1  # Implementation detail

   # Good: Tests behavior
   def test_user_can_login():
       response = client.post("/api/auth/login", ...)
       assert response.status_code == 200
   ```

2. **Hardcoded test data**:
   ```python
   # Bad
   def test_user():
       user = User(email="test@example.com", password="123")

   # Good
   def test_user(test_user_fixture):
       # Use fixture/factory
   ```

3. **Not cleaning up**:
   ```python
   # Bad
   def test_create_user():
       User.create(...)  # Leaves database dirty

   # Good
   @pytest.fixture
   def test_user():
       user = User.create(...)
       yield user
       user.delete()  # Cleanup
   ```

4. **Testing only happy path**:
   ```python
   # Bad - only tests success
   def test_login():
       response = client.post("/api/auth/login", json={...})
       assert response.status_code == 200

   # Good - tests all cases
   def test_login_success(): ...
   def test_login_invalid_credentials(): ...
   def test_login_missing_fields(): ...
   ```

5. **Mocking too much**:
   ```python
   # Bad - mocking everything makes tests brittle
   with patch('auth'), patch('db'), patch('email'):
       # ...

   # Good - only mock external dependencies
   with patch('external_api.call'):
       # ...
   ```

## Test Naming

### Conventions

```python
# Function name: test_<function>_<case>
def test_login_success(): ...
def test_login_invalid_credentials(): ...
def test_login_missing_fields(): ...

# Class name: Test<ClassName>
class TestUserService: ...

# Grouping: Prefix related tests
def test_user_creation(): ...
def test_user_deletion(): ...
def test_user_update(): ...
```

## Running Tests

### All Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run verbose
pytest -v

# Run specific file
pytest tests/test_auth.py

# Run specific test
pytest tests/test_auth.py::test_login_success

# Run failed tests only
pytest --lf

# Run tests matching pattern
pytest -k "login"
```

---

**Remember:** Tests are your safety net. Write them first, keep them fast, maintain them well.
