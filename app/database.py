from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from app.config import get_settings

settings = get_settings()


def convert_postgres_url_to_asyncpg(url: str) -> str:
    """Convert PostgreSQL URL to asyncpg-compatible format"""
    # Replace postgresql:// with postgresql+asyncpg://
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    
    # Parse the URL
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    # Convert sslmode to ssl parameter for asyncpg
    if "sslmode" in query_params:
        sslmode = query_params["sslmode"][0]
        del query_params["sslmode"]
        if sslmode == "require":
            query_params["ssl"] = ["require"]
        elif sslmode == "prefer":
            query_params["ssl"] = ["prefer"]
    
    # Remove channel_binding as asyncpg doesn't support it
    if "channel_binding" in query_params:
        del query_params["channel_binding"]
    
    # Rebuild the URL
    new_query = urlencode(query_params, doseq=True)
    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed)


# Create async engine with connection pooling
db_url = convert_postgres_url_to_asyncpg(settings.DATABASE_URL)
engine = create_async_engine(
    db_url,
    echo=settings.ENVIRONMENT == "development",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
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

