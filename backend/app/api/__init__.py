"""API layer: dependencies, routers and the versioned router assembly."""

from fastapi import APIRouter

from app.api.routes import (
    audience_segments,
    brands,
    cta_rules,
    dashboard,
    execution_logs,
    generations,
    rules,
    templates,
)
from app.api.routes import auth as auth_routes

api_router = APIRouter()
api_router.include_router(auth_routes.router)
api_router.include_router(generations.router)
api_router.include_router(dashboard.router)
api_router.include_router(brands.brands_router)
api_router.include_router(brands.products_router)
api_router.include_router(audience_segments.router)
api_router.include_router(cta_rules.router)
api_router.include_router(rules.router)
api_router.include_router(templates.router)
api_router.include_router(execution_logs.router)

__all__ = ["api_router"]
