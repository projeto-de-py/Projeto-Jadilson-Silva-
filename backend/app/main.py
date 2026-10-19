"""Fabrica da aplicacao FastAPI."""

import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, usuarios
from app.config import get_settings, eh_producao, validar_configuracao_seguranca
from app.core import security
from app.core.ratelimit import Limiter
from app.core.revogados import TokenRevogados

settings = get_settings()

_MUTANTES = {"POST", "PUT", "PATCH", "DELETE"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Em producao, aborta o startup se a config de seguranca estiver fraca
    # (ex.: JWT_SECRET default, cookie sem Secure). Em dev, so avisa.
    validar_configuracao_seguranca()
    yield


def create_app() -> FastAPI:
    # Em producao a documentacao interativa fica desativada (nao expoe rotas).
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url=None if eh_producao() else "/docs",
        openapi_url=None if eh_producao() else "/openapi.json",
    )

    # Estado compartilhado (um unico worker uvicorn - ver core/ratelimit.py e
    # core/revogados.py)
    app.state.limiter = Limiter()
    app.state.revogados = TokenRevogados()

    # IMPORTANTE: o middleware de seguranca/CSRF e registrado ANTES do
    # CORSMiddleware de proposito. O Starlette constroi a pilha de modo que o
    # ultimo add_middleware fica o mais externo - assim o CORS envolve o
    # middleware e as respostas de erro (401/403 do CSRF) tambem recebem os
    # headers Access-Control-Allow-Origin.
    @app.middleware("http")
    async def protecoes(request: Request, call_next):
        """CSRF (double submit via claim no JWT) + headers de seguranca.

        Regra: toda requisicao mutante sob /api precisa do header
        X-CSRF-Token igual ao claim `csrf` embutido no JWT do cookie.
        O proprio login nao entra (ainda nao existe sessao).
        """
        if request.method in _MUTANTES and request.url.path.startswith(
            settings.api_prefix
        ) and request.url.path != f"{settings.api_prefix}/auth/login":
            token = request.cookies.get(settings.auth_cookie_name)
            payload = security.decodificar_token(token) if token else None
            if payload is None:
                return JSONResponse(
                    {"detail": "Sessao expirada. Entre novamente."},
                    status_code=401,
                )
            informado = request.headers.get("X-CSRF-Token", "")
            esperado = payload.get("csrf", "")
            if not informado or not secrets.compare_digest(informado, esperado):
                return JSONResponse(
                    {"detail": "Token CSRF invalido. Atualize a pagina."},
                    status_code=403,
                )

        resp = await call_next(request)
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"  # anti-clickjacking
        resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.auth_cookie_secure:
            # HSTS so faz sentido (e so e seguro) sobre HTTPS
            resp.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains"
            )
        return resp

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,  # frontend Vite
        allow_credentials=True,  # necessario para o cookie de sessao
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Retry-After"],
    )

    prefix = settings.api_prefix
    app.include_router(auth.router, prefix=f"{prefix}/auth", tags=["auth"])
    app.include_router(usuarios.router, prefix=f"{prefix}/usuarios", tags=["usuarios"])

    @app.get("/health", tags=["status"])
    def health() -> dict:
        return {"status": "ok", "versao": settings.app_version}

    return app


app = create_app()
