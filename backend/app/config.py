"""Configuracoes da API lidas do .env (ou variaveis de ambiente)."""

from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr
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
    auth_cookie_samesite: str = "lax"  # ou "strict"

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

    # E-mail da conta do advogado principal (unico ponto de provisionamento do
    # campo `administrador`). Definido por configuracao administrativa - nunca
    # por escolha do usuario em cadastro ou login, e sem credenciais no codigo.
    admin_email: str = "admin@jadilson.adv"

    # IA (ver app/ia). "simulado" nao chama nenhum servico externo;
    # "openrouter" usa um modelo (por padrao o Gemma gratuito do Google) pelo OpenRouter
    # e exige OPENROUTER_API_KEY.
    # Aceita IA_PROVEDOR ou LLM_PROVIDER no .env.
    ia_provedor: str = Field(
        default="simulado",
        validation_alias=AliasChoices("IA_PROVEDOR", "LLM_PROVIDER"),
    )
    ia_limite_sugerir_hora: int = 60  # pedidos de sugestao por usuario/hora
    ia_limite_completar_minuto: int = 40  # autocompletar por usuario/minuto
    # OpenRouter: cole a chave em OPENROUTER_API_KEY no .env (https://openrouter.ai/keys).
    # O padrao e um modelo GRATUITO do Google; a lista muda, confira em https://openrouter.ai/models?q=google%20free
    openrouter_api_key: SecretStr | None = None
    openrouter_model: str = "google/gemma-4-31b-it:free"
    # Modelos reserva (separados por virgula): se o principal estiver saturado, o OpenRouter tenta estes.
    # Testados em 02/11/2026: ambos devolveram JSON valido e bom portugues juridico.
    openrouter_modelos_alternativos: str = "nvidia/nemotron-3-ultra-550b-a55b:free,nvidia/nemotron-3.5-super-vl:free"
    openrouter_api_url: str = "https://openrouter.ai/api/v1/chat/completions"
    # Identificacao opcional do app nos paineis do OpenRouter.
    openrouter_site_url: str = "http://localhost:5173"
    openrouter_app_nome: str = "Jadilson Silva Adv."
    ia_timeout_segundos: int = 60
    ia_max_tokens: int = 2048

    # ZapSign (assinatura eletronica). Segredos nunca vao para log nem resposta.
    assinatura_provedor: str = "autentique"
    autentique_api_url: str = "https://api.autentique.com.br/v2/graphql"
    autentique_api_token: SecretStr | None = None
    autentique_sandbox: bool = False
    autentique_webhook_secret: SecretStr | None = None
    autentique_webhook_header: str = "X-Autentique-Secret"
    zapsign_api_url: str = "https://api.zapsign.com.br/api/v1"
    zapsign_api_token: SecretStr | None = None
    # O webhook e autenticado por um segredo compartilhado, enviado em um header
    # configurado no painel do ZapSign (nome abaixo).
    zapsign_webhook_secret: SecretStr | None = None
    zapsign_webhook_header: str = "X-Zapsign-Secret"

    # Asaas (cobranca). O padrao e o SANDBOX: producao so quando a URL for trocada de proposito.
    asaas_api_url: str = "https://api-sandbox.asaas.com/v3"
    asaas_api_key: SecretStr | None = None
    asaas_webhook_token: SecretStr | None = None  # vem no header `asaas-access-token`

    # Consultas publicas (ver app/integrations). BrasilAPI e Banco Central nao usam chave.
    brasilapi_url: str = "https://brasilapi.com.br/api"
    bcb_sgs_url: str = "https://api.bcb.gov.br/dados/serie"
    # DataJud (CNJ): a chave PUBLICA e divulgada em https://datajud-wiki.cnj.jus.br/api-publica/acesso
    # (o CNJ pode trocar). Sem ela, a consulta de andamentos responde 503.
    datajud_api_url: str = "https://api-publica.datajud.cnj.jus.br"
    datajud_api_key: SecretStr | None = None
    consultas_limite_minuto: int = 60  # consultas externas por usuario/minuto

    # Depois de receber um webhook, confirma o estado direto na API do provedor
    # (defesa extra contra evento forjado ou repetido). Desligue so em testes.
    webhooks_verificar_na_api: bool = True
    integracao_timeout_segundos: int = 20
    # Teto de uma cobranca (R$) para barrar valor digitado errado.
    financeiro_valor_maximo: float = 1_000_000.0

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

    if s.ia_provedor == "openrouter" and not s.openrouter_api_key:
        problemas.append("IA_PROVEDOR=openrouter exige OPENROUTER_API_KEY")
    if s.zapsign_api_token and not s.zapsign_webhook_secret:
        problemas.append("ZAPSIGN_API_TOKEN definido sem ZAPSIGN_WEBHOOK_SECRET (o webhook ficaria sem autenticacao)")
    if s.asaas_api_key and not s.asaas_webhook_token:
        problemas.append("ASAAS_API_KEY definido sem ASAAS_WEBHOOK_TOKEN (o webhook ficaria sem autenticacao)")
    if eh_producao(s) and s.asaas_api_key and "sandbox" in s.asaas_api_url:
        problemas.append("ASAAS_API_URL aponta para o SANDBOX em producao")

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
