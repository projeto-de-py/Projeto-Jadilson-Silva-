"""Configuracoes da API lidas do .env (ou variaveis de ambiente)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "API - Sistema de Gestao de Casos e Agenda"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"

    # Banco de dados (MySQL)
    database_url: str = (
        "mysql+pymysql://root:root@localhost:3306/advocacia?charset=utf8mb4"
    )

    # Autenticacao
    jwt_secret: str = "troque-este-segredo-por-um-valor-aleatorio"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480  # 8 horas

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
