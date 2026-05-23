# Python Best Practices

## When to Use

Use this skill when:
- Writing Python code (new features, bug fixes, refactoring)
- Reviewing Python code (PR reviews, code quality checks)
- Designing Python architecture (system design, patterns)

## Core Principles

### 1. Immutability

Always create new objects, never mutate existing ones.

```python
# ❌ BAD - Mutating
def update_user(user, new_email):
    user.email = new_email
    return user

# ✅ GOOD - Immutable
def update_user(user, new_email):
    return {**user, "email": new_email}

# Or with dataclasses
from dataclasses import dataclass, replace

@dataclass(frozen=True)
class User:
    email: str
    name: str

def update_user(user, new_email):
    return replace(user, email=new_email)
```

### 2. Type Hints

Use type hints on all function signatures.

```python
# ❌ BAD - No type hints
def get_user(user_id):
    return User.query.get(user_id)

# ✅ GOOD - Type hints
from typing import Optional

def get_user(user_id: int) -> Optional[User]:
    return User.query.get(user_id)
```

### 3. Context Managers

Use context managers for resource management.

```python
# ❌ BAD - Manual resource cleanup
file = open("data.txt")
try:
    data = file.read()
finally:
    file.close()

# ✅ GOOD - Context manager
with open("data.txt") as file:
    data = file.read()
```

### 4. List Comprehensions

Use list comprehensions for data transformations.

```python
# ❌ BAD - Manual loop
result = []
for item in items:
    if item > 0:
        result.append(item * 2)

# ✅ GOOD - List comprehension
result = [item * 2 for item in items if item > 0]
```

### 5. Error Handling

Handle errors at every level.

```python
# ❌ BAD - Silent error
def divide(a, b):
    try:
        return a / b
    except:
        pass

# ✅ GOOD - Proper handling
def divide(a: int, b: int) -> float:
    try:
        return a / b
    except ZeroDivisionError:
        raise ValueError("Cannot divide by zero")
```

## Patterns

### Factory Pattern

Create objects without specifying exact classes.

```python
class UserFactory:
    @staticmethod
    def create_user(user_type: str, **kwargs):
        if user_type == "admin":
            return AdminUser(**kwargs)
        elif user_type == "customer":
            return CustomerUser(**kwargs)
        else:
            return User(**kwargs)
```

### Repository Pattern

Abstract data access.

```python
class UserRepository:
    def __init__(self, db_session):
        self.db = db_session

    def find_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter_by(id=user_id).first()

    def create(self, **kwargs) -> User:
        user = User(**kwargs)
        self.db.add(user)
        self.db.commit()
        return user
```

### Strategy Pattern

Define family of algorithms.

```python
class PaymentStrategy(ABC):
    @abstractmethod
    def process(self, amount: float) -> dict:
        pass

class StripePayment(PaymentStrategy):
    def process(self, amount: float) -> dict:
        # Stripe implementation
        pass

class PayPalPayment(PaymentStrategy):
    def process(self, amount: float) -> dict:
        # PayPal implementation
        pass
```

## Anti-Patterns

### ❌ Avoid

1. **Mutable default arguments**
   ```python
   # Bad
   def add_item(item, items=[]):
       items.append(item)

   # Good
   def add_item(item, items=None):
       if items is None:
           items = []
       items.append(item)
   ```

2. **Global variables**
   ```python
   # Bad
   database = None

   def init_db():
       global database
       database = connect()

   # Good
   def init_db():
       return connect()
   ```

3. **Swallowing exceptions**
   ```python
   # Bad
   try:
       risky_operation()
   except:
       pass

   # Good
   try:
       risky_operation()
   except SpecificError as e:
       logger.error(f"Error: {e}")
       raise
   ```

## Performance Tips

### Use Generators

For large datasets, use generators instead of lists.

```python
# ✅ GOOD - Generator (lazy evaluation)
def process_large_file(filename):
    with open(filename) as file:
        for line in file:
            yield line.strip()

# ❌ BAD - List (loads all into memory)
def process_large_file(filename):
    with open(filename) as file:
        return [line.strip() for line in file]
```

### Use Sets for Lookups

Use sets for O(1) lookups.

```python
# ✅ GOOD - Set lookup
allowed_users = {"alice", "bob", "charlie"}
if user in allowed_users:
    # ...

# ❌ BAD - List lookup (O(n))
allowed_users = ["alice", "bob", "charlie"]
if user in allowed_users:
    # ...
```

## Testing

### Unit Tests

Test individual functions in isolation.

```python
import pytest

def test_calculate_discount():
    # Arrange
    user = create_user(is_premium=True)

    # Act
    discount = calculate_discount(user)

    # Assert
    assert discount == 0.2
```

### Fixtures

Use fixtures for test setup.

```python
@pytest.fixture
def test_user():
    user = User.create(
        email="test@example.com",
        password="password123"
    )
    yield user
    user.delete()

def test_user_login(test_user):
    response = client.post("/login", json={
        "email": test_user.email,
        "password": test_user.password
    })
    assert response.status_code == 200
```

## Resources

- [Python Style Guide (PEP 8)](https://peps.org/pep-0008/)
- [Type Hints](https://docs.python.org/3/library/typing.html)
- [Effective Python](https://effectivepython.com/)
- [Python Patterns](https://github.com/faif/python-patterns)
