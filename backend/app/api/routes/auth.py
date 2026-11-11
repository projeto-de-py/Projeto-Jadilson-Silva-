"""RF01: autenticacao - login, sessao atual, logout, senha e configuracoes do escritorio."""

import hashlib

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    _get_revogados,
    get_current_user,
    get_usuario_repo,
)
from app.config import get_settings
from app.core.ratelimit import Limiter
from app.core.revogados import TokenRevogados
from app.database import get_db
from app.models.configuracao_escritorio import ConfiguracaoEscritorio
from app.models.usuario import Usuario
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.auth import (
    AlterarSenhaRequest,
    ConfiguracaoEscritorioIn,
    ConfiguracaoEscritorioOut,
    LoginRequest,
    LoginResponse,
)
from app.schemas.usuario import UsuarioOut
from app.services.auth_service import (
    AuthService,
    ErroAutenticacao,
    UsuarioInativoError,
)

router = APIRouter()
settings = get_settings()


def _get_limiter(request: Request) -> Limiter:
    return request.app.state.limiter


def _ip_do_cliente(request: Request) -> str:
    """IP real do cliente, honrando X-Forwarded-For so quando confiavel."""
    if settings.trust_proxy_headers:
        encaminhado = request.headers.get("x-forwarded-for", "")
        primeiro = encaminhado.split(",")[0].strip()
        if primeiro:
            return primeiro
    return request.client.host if request.client else "desconhecido"


def _obter_ou_criar_configuracao_escritorio(db: Session) -> ConfiguracaoEscritorio:
    ConfiguracaoEscritorio.__table__.create(bind=db.get_bind(), checkfirst=True)
    cfg = db.scalar(select(ConfiguracaoEscritorio).limit(1))
    if cfg is None:
        cfg = ConfiguracaoEscritorio()
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Autenticar usuario (email + senha)",
)
def login(
    dados: LoginRequest,
    request: Request,
    response: Response,
    repo: UsuarioRepository = Depends(get_usuario_repo),
    limiter: Limiter = Depends(_get_limiter),
):
    """RF01: login com rate limit por IP e por e-mail (forca bruta)."""
    ip = _ip_do_cliente(request)
    limiter.check(f"ip:{ip}", settings.rate_limit_login_ip)

    chave_email = (
        "email:"
        + hashlib.sha256(dados.email.strip().lower().encode()).hexdigest()
    )
    limiter.bloqueado(
        chave_email,
        settings.rate_limit_login_email,
        settings.rate_limit_janela_segundos,
    )

    service = AuthService(repo)

    try:
        usuario = service.autenticar(dados.email, dados.senha)
    except ErroAutenticacao:
        limiter.registrar(chave_email, settings.rate_limit_janela_segundos)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "E-mail ou senha invalidos",
        )
    except UsuarioInativoError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc))

    limiter.limpar(chave_email)
    token, csrf = service.gerar_sessao(usuario)
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/",
    )
    return LoginResponse(
        usuario=UsuarioOut.model_validate(usuario), csrf_token=csrf
    )


@router.get(
    "/me",
    response_model=LoginResponse,
    summary="Dados do usuario logado (e novo token CSRF)",
)
@router.get(
    "/session",
    response_model=LoginResponse,
    summary="Alias para /me (compatibilidade com frontend)",
)
def me(
    request: Request,
    usuario: Usuario = Depends(get_current_user),
) -> LoginResponse:
    """Valida a sessao (cookie) e devolve o CSRF atual (pos-reload do front)."""
    return LoginResponse(
        usuario=UsuarioOut.model_validate(usuario),
        csrf_token=request.state.csrf,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Encerrar a sessao (apaga o cookie e revoga o token)",
)
def logout(
    request: Request,
    response: Response,
    _usuario: Usuario = Depends(get_current_user),
    revogados: TokenRevogados = Depends(_get_revogados),
) -> Response:
    """Apaga o cookie de sessao E revoga o `jti` no servidor."""
    revogados.revogar(request.state.jti, request.state.exp)
    resp = Response(status_code=status.HTTP_204_NO_CONTENT)
    resp.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
    )
    return resp


@router.post(
    "/senha",
    response_model=UsuarioOut,
    summary="Alterar senha da conta logada",
)
def alterar_senha(
    dados: AlterarSenhaRequest,
    usuario: Usuario = Depends(get_current_user),
    repo: UsuarioRepository = Depends(get_usuario_repo),
) -> UsuarioOut:
    service = AuthService(repo)
    try:
        atualizado = service.alterar_senha(
            usuario, dados.senha_atual, dados.nova_senha
        )
    except ErroAutenticacao as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return UsuarioOut.model_validate(atualizado)


@router.get(
    "/escritorio",
    response_model=ConfiguracaoEscritorioOut,
    summary="Obter configuracoes gerais do escritorio",
)
def obter_escritorio(
    _usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConfiguracaoEscritorioOut:
    cfg = _obter_ou_criar_configuracao_escritorio(db)
    return ConfiguracaoEscritorioOut.model_validate(cfg)


@router.put(
    "/escritorio",
    response_model=ConfiguracaoEscritorioOut,
    summary="Atualizar configuracoes gerais do escritorio",
)
def atualizar_escritorio(
    dados: ConfiguracaoEscritorioIn,
    _usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConfiguracaoEscritorioOut:
    cfg = _obter_ou_criar_configuracao_escritorio(db)
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        if valor is not None:
            setattr(cfg, campo, valor)
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return ConfiguracaoEscritorioOut.model_validate(cfg)
