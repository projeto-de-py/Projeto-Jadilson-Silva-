"""Fabrica da aplicacao FastAPI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, usuarios
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,  # frontend Vite
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.api_prefix
    app.include_router(auth.router, prefix=f"{prefix}/auth", tags=["auth"])
    app.include_router(usuarios.router, prefix=f"{prefix}/usuarios", tags=["usuarios"])

    @app.get("/health", tags=["status"])
    def health() -> dict:
        return {"status": "ok", "versao": settings.app_version}

    return app


app = create_app()
