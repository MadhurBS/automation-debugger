from __future__ import annotations

import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import init_db
from auth import router as auth_router
from routers.projects import router as projects_router
from routers.analysis import router as analysis_router
from routers.reports import router as reports_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Automation Project Debugger API...")
    await init_db()
    logger.info("Database tables created/verified.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Powered RPA Automation Project Debugger API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health():
    return {"status": "healthy", "version": "1.0.0", "environment": settings.APP_ENV}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=settings.APP_DEBUG)
