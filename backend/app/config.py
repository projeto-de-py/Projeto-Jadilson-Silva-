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

    # Ambiente: "development" (padrao) ou "production".
    # Em production vao valer travas de seguranca obrigatorias (ver
    # validar_configuracao_seguranca abaixo): segredo JWT forte, cookie
    # Secure e docs da API desativados.
    app_env: str = "development"

    # Banco de dados (MySQL)
    database_url: str = (
        "mysql+pymysql://root:root@localhost:3306/advocacia?charset=utf8mb4"
    )

    # Autenticacao
    jwt_secret: str = "HceFer1lr8zbksuUuWagVDRSqzrzFvF2jDWYIj08ZZ9yVggNvLK0jhQGCQ1QDu-OhYa0S1EHnjYgAqmamidSBA"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480  # 8 horas

    # Cookie de sessao (JWT em cookie HttpOnly - nunca acessivel por JS)
    auth_cookie_name: str = "jadilson_token"
    auth_cookie_secure: bool = False  # True em producao (exige HTTPS)
    auth_cookie_samesite: str = "lax"  # "lax" ou "strict"

    # Rate limit do login (janela deslizante em memoria)
    rate_limit_login_ip: int = 20  # requisicoes por IP na janela
    rate_limit_login_email: int = 5  # tentativas por e-mail na janela
    rate_limit_janela_segundos: int = 300  # 5 minutos

    # Confia no header X-Forwarded-For para descobrir o IP real do cliente.
    # So ligue quando houver um proxy/reverse-proxy de confianca (nginx, etc.)
    # na frente da API; caso contrario um atacante pode falsificar o header e
    # escapar do rate limit por IP.
    trust_proxy_headers: bool = False

    # Senha inicial do Admin criada pelo seed (backend/app/seed.py).
    # Se vazio, o seed gera uma senha aleatoria forte e imprime uma unica vez.
    admin_senha_inicial: str | None = None

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Segredos fracos conhecidos (valor default do repo + variacoes obvias). Um
# JWT assinado com qualquer um destes pode ser forjado por qualquer pessoa.
_SECRET_FRACO = {
    "troque-este-segredo-por-um-valor-aleatorio",
    "troque-este-segredo-por-um-valor-aleatorio-bem-grande",
    "change-me",
    "secret",
    "jwt-secret",
}

_MIN_BYTES_SEGREDO = 32  # RFC 7518: HMAC SHA-256 exige chave >= 32 bytes


def eh_producao(settings: Settings | None = None) -> bool:
    """True quando APP_ENV=production."""
    s = settings or get_settings()
    return s.app_env.strip().lower() == "production"


def validar_configuracao_seguranca(settings: Settings | None = None) -> None:
    """Travas de seguranca que falham o startup em producao (fail-fast).

    Em producao, exige: segredo JWT forte (>= 32 bytes e nao default), cookie
    de sessao Secure (HTTPS) e origens CORS sem curinga. Em desenvolvimento
    apenas emite avisos, para nao travar quem esta subindo localmente.
    """
    s = settings or get_settings()
    problemas: list[str] = []

    segredo = s.jwt_secret.strip()
    segredo_fraco = (
        segredo.lower() in _SECRET_FRACO
        or len(segredo.encode("utf-8")) < _MIN_BYTES_SEGREDO
    )
    if segredo_fraco:
        problemas.append(
            "JWT_SECRET e fraco ou nao definido (use pelo menos 32 bytes "
            "aleatorios: python -c \"import secrets; print(secrets.token_urlsafe(64))\")"
        )

    if not s.auth_cookie_secure:
        problemas.append(
            "AUTH_COOKIE_SECURE deve ser true em producao (exige HTTPS)"
        )

    if any("*" in origem for origem in s.cors_origins):
        problemas.append("CORS_ORIGINS nao pode conter curinga (*) em producao")

    if not problemas:
        return

    if eh_producao(s):
        raise RuntimeError(
            "Configuracao de seguranca invalida para PRODUCAO:\n- "
            + "\n- ".join(problemas)
        )

    # desenvolvimento: so avisa, nao impede subir
    import warnings

    for problema in problemas:
        warnings.warn(f"[seguranca/desenvolvimento] {problema}", stacklevel=2)
