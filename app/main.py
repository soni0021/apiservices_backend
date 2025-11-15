from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
from app.config import get_settings
from app.database import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="API Services Platform",
    description="Vehicle RC, Driving Licence, and Challan Verification APIs",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
# ALWAYS include localhost for local development, regardless of environment variables
# This ensures localhost works even when production URLs are set
localhost_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000", 
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:8000",  # In case frontend runs on different port
]

# Get origins from settings (could be from env var or default)
cors_origins = list(settings.cors_origins) if settings.cors_origins else []

# ALWAYS add localhost origins first (for local development)
for origin in localhost_origins:
    if origin not in cors_origins:
        cors_origins.insert(0, origin)  # Insert at beginning to prioritize

# Always include production URLs - handle all Vercel variations
production_origins = [
    "https://apiservices-frountend.vercel.app",
    "https://apiservicesfrountend.vercel.app",
]
for origin in production_origins:
    if origin not in cors_origins:
        cors_origins.append(origin)

# Filter out wildcard patterns (we'll use regex for those)
exact_origins = [origin for origin in cors_origins if '*' not in origin]

# Log CORS origins in development (for debugging)
if settings.ENVIRONMENT == "development":
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"CORS allowed exact origins: {exact_origins}")
    logger.info("CORS also allows all https://*.vercel.app domains via regex")

# CORS configuration: Use both exact origins and regex pattern for Vercel
# This allows:
# 1. Exact matches (localhost, specific Vercel domains)
# 2. All Vercel preview deployments via regex pattern
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r'https://.*\.vercel\.app',  # Allow all Vercel subdomains (preview deployments)
    allow_origins=exact_origins,  # Exact matches for localhost and specific domains
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Add Gzip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "API Services Platform",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }


# Import and include routers
from app.api.v1 import auth, rc, licence, challan, client, admin, public, services
from fastapi import WebSocket, WebSocketDisconnect
from app.websocket.manager import manager
from app.middleware.auth import get_current_user
from app.models.user import UserRole

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(rc.router, prefix="/api/v1", tags=["RC Verification"])
app.include_router(licence.router, prefix="/api/v1", tags=["Licence Verification"])
app.include_router(challan.router, prefix="/api/v1", tags=["Challan Verification"])
app.include_router(client.router, prefix="/api/v1/client", tags=["Client Dashboard"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin Dashboard"])
app.include_router(public.router, prefix="/api/v1/public", tags=["Public"])
app.include_router(services.router, prefix="/api/v1", tags=["Services"])


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for user real-time updates"""
    await manager.connect(websocket, user_id=user_id)
    try:
        while True:
            # Keep connection alive and handle any incoming messages
            data = await websocket.receive_text()
            # Echo back or handle commands
            await websocket.send_json({"type": "pong", "message": "Connection active"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id=user_id)


@app.websocket("/ws/admin")
async def websocket_admin_endpoint(websocket: WebSocket):
    """WebSocket endpoint for admin real-time updates"""
    await manager.connect(websocket, is_admin=True)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            await websocket.send_json({"type": "pong", "message": "Admin connection active"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, is_admin=True)

