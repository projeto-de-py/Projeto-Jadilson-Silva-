"""RF01: autenticacao - login, sessao atual e logout."""

import hashlib

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)

from app.api.deps import (
    _get_revogados,
    get_current_user,
    get_usuario_repo,
)
from app.config import get_settings
from app.core.ratelimit import Limiter
from app.core.revogados import TokenRevogados
from app.models.usuario import Usuario
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.auth import LoginRequest, LoginResponse
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
    """RF01: login com rate limit por IP e por e-mail (forca bruta).

    O JWT e setado como cookie HttpOnly (JS nao le) + SameSite. O corpo da
    resposta traz apenas o usuario e o token CSRF (claim embutido no JWT).

    O limite por IP evita flood; o por e-mail evita forca bruta numa conta.
    As falhas de e-mail sao contadas somente quando a autenticacao falha (para
    nao travar quem esta logando certo) e o bucket e limpo apos um login valido.
    """
    ip = _ip_do_cliente(request)
    limiter.check(f"ip:{ip}", settings.rate_limit_login_ip)

    # Hash do email no bucket: o limiter fica em memoria e nao deve guardar
    # dados pessoais identificaveis.
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
        # conta existe mas esta desativada: nao conta como tentativa de senha
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc))

    limiter.limpar(chave_email)  # login valido: zera o contador da conta
    token, csrf = service.gerar_sessao(usuario)
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,  # inacessivel ao JavaScript (anti-XSS)
        secure=settings.auth_cookie_secure,  # True em producao (HTTPS)
        samesite=settings.auth_cookie_samesite,  # anti-CSRF + UX
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
    """Apaga o cookie de sessao E revoga o `jti` no servidor.

    Revogar e essencial: sem isso, um token roubado continuaria valido ate
    expirar mesmo depois do usuario deslogar. Exige token CSRF (mutacao sem
    CSRF nao passa pelo middleware).
    """
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
