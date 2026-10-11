from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.database.session import async_engine, AsyncSessionLocal
from app.database.base import Base
from app.api.v1 import api_v1_router
from app.services.rag_service import KnowledgeService
# Ensure models are loaded
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist in dev/prototype mode
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed initial knowledge base
    async with AsyncSessionLocal() as db:
        await KnowledgeService.seed_initial_knowledge(db)

    yield
    # Shutdown
    await async_engine.dispose()




app = FastAPI(
    title=f"{settings.PROJECT_NAME} - {settings.INSTITUTION_NAME} Admission API",
    description=(
        f"Core backend API for {settings.PROJECT_NAME} Prototype ({settings.ACADEMIC_YEAR}).\n\n"
        "**NOTE:** This system operates strictly in PROTOTYPE/SIMULATION mode with synthetic demo data."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health", tags=["Health & Status"])
async def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "institution": settings.INSTITUTION_NAME,
        "institution_code": settings.INSTITUTION_CODE,
        "academic_year": settings.ACADEMIC_YEAR,
        "environment": settings.ENVIRONMENT,
    }


# Include API Routers
app.include_router(api_v1_router)
