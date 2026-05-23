"""
Database models and connection management.
Agents share context through the database.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, 
    ForeignKey, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.pool import StaticPool
import enum

Base = declarative_base()


class StoryStatus(enum.Enum):
    """Story workflow states."""
    PM_REVIEW = "pm-review"
    READY_PLANNER = "ready-planner"
    READY_ARCHITECT = "ready-architect"
    APPROVED = "approved"
    DEV = "dev"
    QA = "qa"
    HUMAN_REVIEW = "human-review"
    DONE = "done"


class TaskStatus(enum.Enum):
    """Task workflow states."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class Story(Base):
    """
    A user story or feature request.
    Contains full context for handoffs between agents.
    """
    __tablename__ = "stories"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(SQLEnum(StoryStatus), default=StoryStatus.PM_REVIEW)
    priority = Column(String(50), default="medium")  # low, medium, high, critical
    
    # Assignment
    assigned_agent = Column(String(100))  # Which agent is currently working on it
    github_issue_number = Column(Integer)  # Linked GitHub issue
    
    # Full context - this is how agents pass information
    context_json = Column(JSON, default=dict)  # Conversation history, decisions, constraints
    acceptance_criteria = Column(JSON, default=list)  # List of criteria
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    tasks = relationship("Task", back_populates="story", cascade="all, delete-orphan")
    comments = relationship("StoryComment", back_populates="story", cascade="all, delete-orphan")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for LLM context."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority,
            "assigned_agent": self.assigned_agent,
            "context": self.context_json,
            "acceptance_criteria": self.acceptance_criteria,
            "created_at": self.created_at.isoformat(),
            "tasks": [t.to_dict() for t in self.tasks],
        }


class Task(Base):
    """
    A granular task broken down from a story.
    """
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.TODO)
    
    # Assignment
    assigned_agent = Column(String(100))
    estimate_hours = Column(Integer, nullable=True)
    
    # Dependencies
    dependencies = Column(JSON, default=list)  # List of task IDs this depends on
    
    # Output
    output_json = Column(JSON, default=dict)  # Results, code snippets, decisions
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    story = relationship("Story", back_populates="tasks")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for LLM context."""
        return {
            "id": self.id,
            "story_id": self.story_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "assigned_agent": self.assigned_agent,
            "estimate_hours": self.estimate_hours,
            "output": self.output_json,
        }


class StoryComment(Base):
    """
    Comments on a story (e.g., agent questions, human answers).
    """
    __tablename__ = "story_comments"
    
    id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    author = Column(String(100), nullable=False)  # Agent name or "human"
    content = Column(Text, nullable=False)
    comment_type = Column(String(50), default="note")  # note, question, answer, decision
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    story = relationship("Story", back_populates="comments")

    def to_dict(self) -> dict:
        """Convert to dictionary for LLM context."""
        return {
            "id": self.id,
            "story_id": self.story_id,
            "author": self.author,
            "content": self.content,
            "comment_type": self.comment_type,
            "created_at": self.created_at.isoformat(),
        }


class AgentLog(Base):
    """
    Audit log of all agent actions.
    """
    __tablename__ = "agent_logs"
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(String(100), nullable=False)
    action = Column(String(200), nullable=False)
    story_id = Column(Integer, nullable=True)
    task_id = Column(Integer, nullable=True)
    
    # Full context of what happened
    input_context = Column(JSON, default=dict)
    output = Column(JSON, default=dict)
    decisions_made = Column(JSON, default=list)
    questions_asked = Column(JSON, default=list)
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow)
    duration_ms = Column(Integer, nullable=True)
    success = Column(Integer, default=1)  # 1 = success, 0 = failure
    error_message = Column(Text, nullable=True)


class ChannelMessage(Base):
    """
    Agent-to-agent broadcast messages.
    Think of it like a shared inbox where any agent can post,
    and any agent (or human) can read the full conversation history.
    
    Example:
      architect  → "picked_up"    → Story #3 ready for design
      architect  → "approved"    → Story #3 cleared for dev
      developer  → "picked_up"   → Story #3 assigned to me
      developer  → "created_pr"  → PR #47 for Story #3
      qa         → "picked_up"   → Story #3 in testing
      qa         → "passed"      → Story #3 all tests green
    """
    __tablename__ = "channel_messages"
    
    id = Column(Integer, primary_key=True)
    
    # Who sent it
    agent_id = Column(String(100), nullable=False)  # e.g. "aco-architect"
    
    # What happened — standard verbs:
    #   picked_up, approved, rejected, returned, created_pr,
    #   tests_passed, tests_failed, escalated, commented, done
    verb = Column(String(50), nullable=False)
    
    # Which story this relates to (optional for system messages)
    story_id = Column(Integer, nullable=True)
    
    # Human-readable broadcast content
    content = Column(Text, nullable=False)
    
    # Extra structured data (e.g. PR number, task list, diff stats)
    extra_data = Column(JSON, default=dict)
    
    # Timestamp + ordering
    timestamp = Column(DateTime, default=datetime.utcnow)


# Database connection
engine = None
SessionLocal = None


def init_database(database_url: str):
    """Initialize database connection and create tables."""
    global engine, SessionLocal
    
    # Handle SQLite vs PostgreSQL
    if database_url.startswith("sqlite"):
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )
    else:
        engine = create_engine(database_url, echo=False)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return engine


def get_session():
    """Get a database session."""
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return SessionLocal()


def close_database():
    """Close database connection."""
    if engine:
        engine.dispose()
