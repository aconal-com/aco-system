"""
Configuration management for ACO system.
Loads from environment variables and .env file.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # GitHub
    GITHUB_TOKEN: str = Field(..., description="GitHub Personal Access Token")
    GITHUB_OWNER: str = Field(..., description="GitHub username/org")
    GITHUB_REPO: str = Field(..., description="Main repo name")
    
    # LLM Provider
    LLM_PROVIDER: str = Field("anthropic", description="openai, anthropic, xai, openrouter, or minimax")
    OPENAI_API_KEY: str | None = Field(None, description="OpenAI API key")
    ANTHROPIC_API_KEY: str | None = Field(None, description="Anthropic API key")
    XAI_API_KEY: str | None = Field(None, description="X.AI API key")
    OPENROUTER_API_KEY: str | None = Field(None, description="OpenRouter API key")
    OPENROUTER_MODEL: str = Field("minimax/minimax-m2.5", description="OpenRouter model to use (e.g., minimax/minimax-m2.5)")
    MINIMAX_API_KEY: str | None = Field(None, description="MiniMax API key")
    MINIMAX_MODEL: str = Field("MiniMax-M2.7", description="MiniMax model to use")

    # LLM Model Mappings (Current models as of 2025)
    MODEL_OPU: str = Field("claude-opus-4-20250514", description="Opus model for complex reasoning")
    MODEL_SONNET: str = Field("claude-sonnet-4-20250514", description="Sonnet model for implementation")
    MODEL_HAIKU: str = Field("claude-haiku-4-20250514", description="Haiku model for status updates")

    # Agent Model Assignments
    AGENT_MODELS: dict = Field(
        default={
            "aco-pm": "MODEL_SONNET",
            "aco-planner": "MODEL_OPU",
            "aco-architect": "MODEL_OPU",
            "aco-dev": "MODEL_SONNET",
            "aco-qa": "MODEL_SONNET",
            "aco-human": "none",  # No LLM needed for human reviewer
        },
        description="Which model each agent uses (maps to MODEL_* keys or 'none')"
    )
    
    # Database
    DATABASE_URL: str = Field("sqlite:///./data/aco.db", description="Database connection string")
    
    # Redis (optional)
    REDIS_URL: str | None = Field(None, description="Redis connection string")
    
    # Logging
    LOG_LEVEL: str = Field("INFO", description="Logging level")
    LOG_FORMAT: str = Field("json", description="json or text")
    
    # Agent Settings
    AGENT_POLL_INTERVAL_SECONDS: int = Field(30, description="Seconds between agent polls")
    MAX_RETRY_ATTEMPTS: int = Field(3, description="Max retry attempts on failure")
    AGENT_PROMPTS_DIR: str = Field("agent_prompts", description="Directory containing agent prompt markdown files")
    RULES_DIR: str = Field("rules", description="Directory containing rule files")
    SKILLS_DIR: str = Field("skills", description="Directory containing skill files")
    CONTEXTS_DIR: str = Field("contexts", description="Directory containing project context files")
    HOOKS_DIR: str = Field("hooks", description="Directory containing hook JSON configs")

    # Context Management
    MAX_CONTEXT_TOKENS: int = Field(128000, description="Max tokens before context trimming")
    RECENT_COMMENTS_COUNT: int = Field(10, description="Keep this many recent comments unsummarized")
    
    # Human Contact
    HUMAN_CONTACT_METHOD: str = Field("whatsapp", description="How to contact human")
    HUMAN_PHONE: str = Field("+1234567890", description="Human's phone number")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        case_sensitive = True


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
