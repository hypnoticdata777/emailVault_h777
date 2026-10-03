from __future__ import annotations

from fastapi import FastAPI

from services.api.app.api.demo import router as demo_router
from services.api.app.api.routes import api_error_handler, router
from services.api.app.api.web import router as web_router
from services.api.app.domain.contracts import ApiError


# PROJECT BEACON: This is the composition root; start here to see every app surface.
def create_app() -> FastAPI:
    app = FastAPI(title="Email Vault API", version="0.2.0")
    app.include_router(router)
    app.include_router(demo_router)
    app.include_router(web_router)
    app.add_exception_handler(ApiError, api_error_handler)
    return app


app = create_app()
