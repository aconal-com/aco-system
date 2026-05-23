# FastAPI Best Practices

## When to Use

Use this skill when:
- Building REST APIs with FastAPI
- Designing API endpoints and routes
- Implementing request/response handling
- Reviewing FastAPI code

## Core Principles

### 1. Pydantic Models

Use Pydantic for request/response validation.

```python
from pydantic import BaseModel, EmailStr, Field

class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)

@app.post("/users")
async def create_user(request: CreateUserRequest):
    user = User.create(**request.dict())
    return user.to_dict()
```

### 2. Dependency Injection

Use FastAPI's dependency system.

```python
from fastapi import Depends, HTTPException, Header

def get_current_user(authorization: str = Header(...)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.replace("Bearer ", "")
    return decode_token(token)

@app.get("/users/me")
async def get_user(current_user: User = Depends(get_current_user)):
    return current_user
```

### 3. Exception Handling

Use HTTPException for errors.

```python
from fastapi import HTTPException

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    user = User.query.get(user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User {user_id} not found"
        )
    return user
```

### 4. Async/Await

Use async/await for I/O operations.

```python
import asyncio

@app.post("/process")
async def process_data(data: ProcessRequest):
    # Async database operation
    user = await asyncio.to_thread(User.create, **data.dict())
    # Async external API call
    result = await call_external_api(data)
    return result
```

## Routing

### Path Parameters

```python
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return User.query.get(user_id)
```

### Query Parameters

```python
from typing import Optional

@app.get("/users")
async def list_users(
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None
):
    query = User.query
    if search:
        query = query.filter(User.name.contains(search))
    return query.offset(skip).limit(limit).all()
```

### Request Body

```python
class UpdateUserRequest(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None

@app.put("/users/{user_id}")
async def update_user(user_id: int, request: UpdateUserRequest):
    user = User.query.get(user_id)
    if not user:
        raise HTTPException(status_code=404)
    # Update only provided fields
    if request.email:
        user.email = request.email
    if request.name:
        user.name = request.name
    return user
```

## Response Format

### Consistent Envelope

```python
from typing import Generic, TypeVar, Optional

T = TypeVar('T')

class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    user = User.query.get(user_id)
    if user:
        return APIResponse(success=True, data=user)
    else:
        return APIResponse(success=False, error="User not found")
```

### Pagination

```python
class PaginatedResponse(BaseModel, Generic[T]):
    success: bool
    data: List[T]
    total: int
    page: int
    pages: int

@app.get("/users")
async def list_users(page: int = 1, per_page: int = 20):
    offset = (page - 1) * per_page
    users = User.query.offset(offset).limit(per_page).all()
    total = User.query.count()
    pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        success=True,
        data=users,
        total=total,
        page=page,
        pages=pages
    )
```

## Middleware

### CORS

```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Logging

```python
import logging
from fastapi import Request

app = FastAPI()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"{request.method} {request.url}")
    response = await call_next(request)
    return response
```

## Security

### Authentication

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

@app.get("/protected")
async def protected_route(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user
```

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/endpoint")
@limiter.limit("10/minute")
async def api_endpoint():
    return {"message": "Hello"}
```

## Validation

### Custom Validators

```python
from pydantic import validator

class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)

    @validator('password')
    def password_strength(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        return v
```

### Error Responses

```python
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "errors": exc.errors()},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error"},
    )
```

## Testing

### Test Client

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_user():
    response = client.post(
        "/users",
        json={
            "email": "test@example.com",
            "password": "password123",
            "name": "Test User"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == "test@example.com"
```

### Mock Database

```python
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_db():
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = Mock()
    return db

def test_get_user(mock_db):
    user = get_user(1, db=mock_db)
    assert user is not None
```

## Performance

### Database Pooling

```python
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20
)
```

### Async Database

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

engine = create_async_engine(DATABASE_URL)

async with AsyncSession(engine) as session:
    users = await session.execute(select(User))
```

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://pydantic-docs.helpmanual.io/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html)
