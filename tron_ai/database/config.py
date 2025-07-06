"""Database configuration for conversation history tracking."""

from pydantic import BaseModel, Field
from typing import Optional
from pathlib import Path

class DatabaseConfig(BaseModel):
    """Configuration for the conversation history database."""
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/conversations.db",
        description="Database connection URL"
    )
    echo: bool = Field(
        default=False,
        description="Whether to echo SQL statements (for debugging)"
    )
    pool_size: int = Field(
        default=10,
        description="Connection pool size for async operations",
        ge=1,
        le=50
    )
    max_overflow: int = Field(
        default=20,
        description="Maximum overflow connections",
        ge=0
    )
    pool_timeout: int = Field(
        default=30,
        description="Connection pool timeout in seconds",
        ge=1
    )
    pool_recycle: int = Field(
        default=3600,
        description="Connection recycle time in seconds",
        ge=60
    )
    database_path: Path = Field(
        default=Path("./data"),
        description="Path to the database directory"
    )

    def __init__(self, **data):
        super().__init__(**data)
        # Ensure database directory exists
        self.database_path.mkdir(parents=True, exist_ok=True)
        # Update database_url if using default path
        if self.database_url.startswith("sqlite+aiosqlite:///./data/"):
            self.database_url = f"sqlite+aiosqlite:///{self.database_path}/conversations.db" 