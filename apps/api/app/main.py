import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine
from app.api.v1 import auth, workspaces, sources, connections, knowledge, query, reports

# Ensure data directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.SANDBOX_DIR, exist_ok=True)
os.makedirs("./data/duckdb", exist_ok=True)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="DataPilot — Business Analytics You Can Verify"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Auth"])
app.include_router(workspaces.router, prefix=f"{settings.API_V1_STR}/workspaces", tags=["Workspaces"])
app.include_router(sources.router, prefix=f"{settings.API_V1_STR}/sources", tags=["Data Sources"])
app.include_router(connections.router, prefix=f"{settings.API_V1_STR}/connections", tags=["Database Connections"])
app.include_router(knowledge.router, prefix=f"{settings.API_V1_STR}/knowledge", tags=["Business Knowledge"])
app.include_router(query.router, prefix=f"{settings.API_V1_STR}/query", tags=["Ask Data"])
app.include_router(reports.router, prefix=f"{settings.API_V1_STR}/reports", tags=["Reports & Dashboards"])

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "default_llm_provider": settings.DEFAULT_LLM_PROVIDER
    }
