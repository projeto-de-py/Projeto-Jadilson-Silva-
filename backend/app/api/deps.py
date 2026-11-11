"""Dependencias compartilhadas (Dependency Injection do FastAPI)."""

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core import security
from app.core.revogados import TokenRevogados
from app.database import get_db
from app.models.usuario import Perfil, Usuario
from app.repositories.caso_historico_repository import CasoHistoricoRepository
from app.repositories.caso_repository import CasoRepository
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.compromisso_historico_repository import (
    CompromissoHistoricoRepository,
)
from app.repositories.compromisso_repository import CompromissoRepository
from app.repositories.prazo_historico_repository import PrazoHistoricoRepository
from app.repositories.prazo_repository import PrazoRepository
from app.repositories.processo_historico_repository import ProcessoHistoricoRepository
from app.repositories.processo_judicial_repository import ProcessoJudicialRepository
from app.repositories.usuario_caso_repository import UsuarioCasoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.services.caso_service import CasoService
from app.services.compromisso_service import CompromissoService
from app.services.permissao_service import PermissaoCasoService
from app.services.prazo_service import PrazoService
from app.services.processo_service import ProcessoJudicialService

settings = get_settings()


# ------------------------------------------------------------ repositories

def get_usuario_repo(db: Session = Depends(get_db)) -> UsuarioRepository:
    return UsuarioRepository(db)


def get_caso_repo(db: Session = Depends(get_db)) -> CasoRepository:
    return CasoRepository(db)


def get_caso_historico_repo(db: Session = Depends(get_db)) -> CasoHistoricoRepository:
    return CasoHistoricoRepository(db)


def get_processo_repo(db: Session = Depends(get_db)) -> ProcessoJudicialRepository:
    return ProcessoJudicialRepository(db)


def get_processo_historico_repo(db: Session = Depends(get_db)) -> ProcessoHistoricoRepository:
    return ProcessoHistoricoRepository(db)


def get_cliente_repo(db: Session = Depends(get_db)) -> ClienteRepository:
    return ClienteRepository(db)


def get_prazo_repo(db: Session = Depends(get_db)) -> PrazoRepository:
    return PrazoRepository(db)


def get_prazo_historico_repo(db: Session = Depends(get_db)) -> PrazoHistoricoRepository:
    return PrazoHistoricoRepository(db)


def get_compromisso_repo(db: Session = Depends(get_db)) -> CompromissoRepository:
    return CompromissoRepository(db)


def get_compromisso_historico_repo(
    db: Session = Depends(get_db),
) -> CompromissoHistoricoRepository:
    return CompromissoHistoricoRepository(db)


def get_usuario_caso_repo(db: Session = Depends(get_db)) -> UsuarioCasoRepository:
    return UsuarioCasoRepository(db)


# --------------------------------------------------------------- services

def get_permissao_service(
    permissoes: UsuarioCasoRepository = Depends(get_usuario_caso_repo),
    usuarios: UsuarioRepository = Depends(get_usuario_repo),
    casos: CasoRepository = Depends(get_caso_repo),
) -> PermissaoCasoService:
    return PermissaoCasoService(permissoes=permissoes, usuarios=usuarios, casos=casos)


def get_caso_service(
    casos: CasoRepository = Depends(get_caso_repo),
    historico: CasoHistoricoRepository = Depends(get_caso_historico_repo),
    clientes: ClienteRepository = Depends(get_cliente_repo),
    usuarios: UsuarioRepository = Depends(get_usuario_repo),
    permissoes: UsuarioCasoRepository = Depends(get_usuario_caso_repo),
) -> CasoService:
    return CasoService(
        casos=casos,
        historico=historico,
        clientes=clientes,
        usuarios=usuarios,
        permissoes=permissoes,
    )


def get_processo_service(
    processos: ProcessoJudicialRepository = Depends(get_processo_repo),
    historico: ProcessoHistoricoRepository = Depends(get_processo_historico_repo),
    casos: CasoRepository = Depends(get_caso_repo),
    permissoes: UsuarioCasoRepository = Depends(get_usuario_caso_repo),
) -> ProcessoJudicialService:
    return ProcessoJudicialService(
        processos=processos,
        historico=historico,
        casos=casos,
        permissoes=permissoes,
    )


def get_prazo_service(
    prazos: PrazoRepository = Depends(get_prazo_repo),
    historico: PrazoHistoricoRepository = Depends(get_prazo_historico_repo),
    casos: CasoRepository = Depends(get_caso_repo),
    permissoes: UsuarioCasoRepository = Depends(get_usuario_caso_repo),
    usuarios: UsuarioRepository = Depends(get_usuario_repo),
    processos: ProcessoJudicialRepository = Depends(get_processo_repo),
) -> PrazoService:
    return PrazoService(
        prazos=prazos,
        historico=historico,
        casos=casos,
        permissoes=permissoes,
        usuarios=usuarios,
        processos=processos,
    )


def get_compromisso_service(
    compromissos: CompromissoRepository = Depends(get_compromisso_repo),
    historico: CompromissoHistoricoRepository = Depends(get_compromisso_historico_repo),
    casos: CasoRepository = Depends(get_caso_repo),
    permissoes: UsuarioCasoRepository = Depends(get_usuario_caso_repo),
    usuarios: UsuarioRepository = Depends(get_usuario_repo),
    processos: ProcessoJudicialRepository = Depends(get_processo_repo),
) -> CompromissoService:
    return CompromissoService(
        compromissos=compromissos,
        historico=historico,
        casos=casos,
        permissoes=permissoes,
        usuarios=usuarios,
        processos=processos,
    )


# ------------------------------------------------------- autenticacao/autorizacao

def _get_revogados(request: Request) -> TokenRevogados:
    return request.app.state.revogados


def _sub_valido(payload: dict) -> int | None:
    """Extrai o id do usuario a partir do claim `sub`, tolerando tokens malformados.

    Sem isto, um JWT assinado corretamente mas sem `sub` (ou com `sub` nao
    numerico) estourava KeyError/ValueError e virava 500 em vez de 401.
    """
    sub = payload.get("sub")
    try:
        return int(sub)
    except (TypeError, ValueError):
        return None


def get_current_user(
    request: Request,
    token: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
    repo: UsuarioRepository = Depends(get_usuario_repo),
    revogados: TokenRevogados = Depends(_get_revogados),
) -> Usuario:
    """Usuario autenticado a partir do JWT no cookie HttpOnly (RF01).

    O payload tambem e guardado em request.state para o handler de /me
    recuperar o claim `csrf` (o cookie e invisivel para o JavaScript) e para o
    logout recuperar `jti`/`exp` e revogar a sessao.

    Usuario desativado tambem cai aqui (401): quem foi bloqueado pelo
    advogado principal perde imediatamente o acesso a toda rota protegida.
    """
    if not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Sessao expirada. Entre novamente.",
        )

    payload = security.decodificar_token(token)
    if payload is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Sessao expirada. Entre novamente.",
        )

    if revogados.esta_revogado(payload.get("jti")):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Sessao expirada. Entre novamente.",
        )

    usuario_id = _sub_valido(payload)
    if usuario_id is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Sessao expirada. Entre novamente.",
        )

    usuario = repo.buscar_por_id(usuario_id)
    if usuario is None or not usuario.ativo:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Usuario nao encontrado ou inativo",
        )

    request.state.csrf = payload.get("csrf", "")
    request.state.jti = payload.get("jti")
    request.state.exp = payload.get("exp")
    return usuario


def require_admin(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    """Bloqueia quem nao for advogado principal (RF02/RF07/RF08).

    A condicao e a permissao administrativa da conta (`usuario.administrador`),
    nao o perfil funcional - colaborador e funcionario nunca passam por aqui.
    """
    if not usuario.administrador:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Acesso restrito ao advogado principal (administrador)",
        )
    return usuario


def require_advogado(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    """Bloqueia funcionarios de operacoes que exigem formacao juridica.

    Criar/editar caso e ato de advogado (Fase 2): o administrador tambem passa
    por aqui, pois o perfil dele e ADVOGADO.
    """
    if usuario.perfil != Perfil.ADVOGADO.value:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Operacao restrita a advogados",
        )
    return usuario
