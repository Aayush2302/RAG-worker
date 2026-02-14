# config/env.py
import os
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment file based on NODE_ENV
env_file = ".env.production" if os.getenv("NODE_ENV") == "production" else ".env.development"
load_dotenv(dotenv_path=env_file)


class Settings(BaseSettings):
    """
    Environment configuration with validation
    Matches TypeScript env.ts schema
    """
    PORT: int = Field(default=5000, ge=1, le=65535)
    
    MONGO_URI: str = Field(min_length=1)
    
    NODE_ENV: Literal["development", "production", "test"] = "development"
    
    # 🔒 CRITICAL - Redis connection for BullMQ
    REDIS_URL: str = Field(min_length=1, description="Redis URL is required for BullMQ")
    
    # Supabase configuration
    SUPABASE_URL: str = Field(min_length=1)
    SUPABASE_SERVICE_ROLE_KEY: str = Field(min_length=1)
    
    # Jina AI API Key (for embeddings)
    JINA_API_KEY: str = Field(default="", description="Jina AI API key for embeddings")
    
    @field_validator('REDIS_URL')
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        if not v:
            raise ValueError("REDIS_URL is required")
        return v
    
    class Config:
        env_file = env_file
        case_sensitive = True


# Singleton instance
try:
    env = Settings()
    print("✅ Environment variables loaded successfully")
except Exception as e:
    print(f"❌ Invalid environment variables: {e}")
    exit(1)
