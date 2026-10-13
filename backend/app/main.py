from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import advanced, analytics, cpi, dashboard, datasets, insights, system

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create all database tables
    Base.metadata.create_all(bind=engine)
    yield
    # Teardown
    engine.dispose()


app = FastAPI(
    title="InsightAI API",
    description="AI-Powered Business Intelligence & Data Analytics Copilot — Complete 5-Phase Engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["health"])
def health_check():
    return {
        "status": "ok",
        "version": "1.0.0",
        "service": "InsightAI Data & Analytics Platform",
        "capabilities": [
            "data_profiling",
            "data_cleaning",
            "nl_to_sql",
            "executive_dashboard",
            "statistical_insights",
            "anomaly_detection",
            "time_series_forecasting",
        ],
    }


# Register feature routers
app.include_router(datasets.router)
app.include_router(analytics.router)
app.include_router(dashboard.router)
app.include_router(insights.router)
app.include_router(advanced.router)
app.include_router(system.router)
app.include_router(cpi.router)
