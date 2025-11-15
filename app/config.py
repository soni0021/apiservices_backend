from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables with hardcoded defaults"""
    
    # Database - Hardcoded default (fallback to Neon DB if .env not provided)
    # Can be overridden via .env file or environment variable
    DATABASE_URL: str = "postgresql://neondb_owner:npg_iE6tsGWjex0L@ep-floral-sun-a4ivcahj-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"
    
    # JWT Configuration - Hardcoded defaults
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-this-in-production-minimum-32-characters"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # External APIs - Hardcoded defaults (empty means not configured)
    EXTERNAL_API_1_URL: str = ""
    EXTERNAL_API_1_KEY: str = ""
    EXTERNAL_API_2_URL: str = ""
    EXTERNAL_API_2_KEY: str = ""
    EXTERNAL_API_3_URL: str = ""
    EXTERNAL_API_3_KEY: str = ""
    
    # Redis - Hardcoded default
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # CORS - Hardcoded defaults with production frontend URLs and localhost
    # Always includes localhost for local development
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,https://apiservices-frountend.vercel.app,https://apiservicesfrountend.vercel.app"
    
    # API Configuration - Hardcoded defaults
    API_RATE_LIMIT_PER_MINUTE: int = 100
    RC_DATA_TTL_HOURS: int = 24
    DL_DATA_TTL_HOURS: int = 168
    CHALLAN_DATA_TTL_HOURS: int = 12
    
    # Environment - Hardcoded default
    ENVIRONMENT: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

