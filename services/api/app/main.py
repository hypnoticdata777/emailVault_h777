from __future__ import annotations

from fastapi import FastAPI

from services.api.app.api.routes import api_error_handler, router
from services.api.app.domain.contracts import ApiError


def create_app() -> FastAPI:
    app = FastAPI(title="Email Vault API", version="0.2.0")
    app.include_router(router)
    app.add_exception_handler(ApiError, api_error_handler)
    return app


app = create_app()

