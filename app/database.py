from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from app.config import get_settings

settings = get_settings()


def convert_postgres_url_to_asyncpg(url: str) -> str:
    """
    Convert PostgreSQL URL to asyncpg-compatible format.
    Handles various URL formats and removes unsupported parameters.
    """
    if not url:
        raise ValueError("DATABASE_URL cannot be empty")
    
    # Replace postgresql:// with postgresql+asyncpg://
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql+asyncpg://"):
        # Already in correct format
        pass
    else:
        # If it doesn't start with postgresql://, assume it needs the prefix
        if not url.startswith("postgresql"):
            raise ValueError(f"Invalid DATABASE_URL format: {url[:50]}...")
    
    # Parse the URL
    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
    except Exception as e:
        raise ValueError(f"Failed to parse DATABASE_URL: {str(e)}")
    
    # Convert sslmode to ssl parameter for asyncpg
    if "sslmode" in query_params:
        sslmode = query_params["sslmode"][0].lower()
        del query_params["sslmode"]
        # asyncpg uses ssl parameter, not sslmode
        if sslmode in ["require", "prefer", "allow"]:
            query_params["ssl"] = ["require"]
        elif sslmode == "disable":
            # Don't set ssl parameter if disabled
            pass
    
    # Remove channel_binding as asyncpg doesn't support it
    # This is critical for Neon and other providers that include it
    if "channel_binding" in query_params:
        del query_params["channel_binding"]
    
    # Remove other unsupported parameters
    unsupported_params = ["connect_timeout", "application_name"]
    for param in unsupported_params:
        if param in query_params:
            del query_params[param]
    
    # Rebuild the URL
    new_query = urlencode(query_params, doseq=True)
    new_parsed = parsed._replace(query=new_query)
    converted_url = urlunparse(new_parsed)
    
    return converted_url


# Create async engine with connection pooling
# Convert database URL and handle errors gracefully
try:
    db_url = convert_postgres_url_to_asyncpg(settings.DATABASE_URL)
except Exception as e:
    raise ValueError(
        f"Failed to convert DATABASE_URL: {str(e)}\n"
        f"Please check your DATABASE_URL in .env file or environment variables."
    ) from e

# Create engine with proper SSL configuration for Neon and other cloud providers
engine = create_async_engine(
    db_url,
    echo=settings.ENVIRONMENT == "development",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,   # Recycle connections after 1 hour
    connect_args={
        "server_settings": {
            "application_name": "apiservices_backend",
        }
    } if settings.ENVIRONMENT == "production" else {},
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from app.models import (
            user, api_key, rc_data, licence_data, challan_data, usage_log,
            industry, category, service, service_industry, subscription, transaction,
            rc_mobile_data, pan_data, address_verification_data, fuel_price_data,
            gst_data, msme_data, udyam_data, voter_id_data, dl_challan_data
        )
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

