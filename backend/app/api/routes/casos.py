"""Gerenciamento de casos e gestao de acesso por caso (Fases 1 e 2).

A visibilidade e decidida no servidor (repositories/escopo.py): esconder
botoes no frontend nao e suficiente. Sem autenticacao responde 401; autenticado
sem autorizacao responde 403 (operacoes administrativas/de edicao) ou 404
(caso fora do escopo, para nao revelar que ele existe).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status as http_status

from app.api.deps import (
    get_caso_repo,
    get_caso_service,
    get_current_user,
    get_permissao_service,
    require_admin,
    require_advogado,
)
from app.models.caso import Caso
from app.models.caso_historico import CasoHistorico
from app.models.usuario import Usuario
from app.models.usuario_caso import UsuarioCaso
from app.repositories.caso_repository import CasoRepository
from app.schemas.caso import (
    CasoCreate,
    CasoOut,
    CasoPaginaOut,
    CasoUpdate,
    HistoricoOut,
)
from app.schemas.permissao import PermissaoCasoCreate, PermissaoCasoOut
from app.services.caso_service import (
    CasoJaArquivadoError,
    CasoNaoEncontradoError,
    CasoService,
    NumeroProcessoDuplicadoError,
    PermissaoEdicaoNegadaError,
    ResponsavelInvalidoError,
)
from app.services.cliente_service import ClienteNaoEncontradoError, DadosInvalidosError
from app.services.permissao_service import (
    AutoConcessaoNegadaError,
    PermissaoCasoService,
    PermissaoJaExistenteError,
    PermissaoNaoEncontradaError,
)
from app.services.usuario_service import (
    DadosInvalidosError as DadosInvalidosUsuarioError,
)
from app.services.usuario_service import (
    UsuarioNaoEncontradoError,
)

router = APIRouter()


def _mapear_erros_caso(exc: Exception) -> HTTPException:
    """Traduz os erros de negocio do CasoService para HTTP (sem logica no router)."""
    if isinstance(exc, CasoNaoEncontradoError):
        return HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, ClienteNaoEncontradoError):
        return HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, ResponsavelInvalidoError):
        return HTTPException(http_status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    if isinstance(exc, (DadosInvalidosError, DadosInvalidosUsuarioError)):
        return HTTPException(http_status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    if isinstance(exc, PermissaoEdicaoNegadaError):
        return HTTPException(http_status.HTTP_403_FORBIDDEN, str(exc))
    if isinstance(exc, NumeroProcessoDuplicadoError):
        return HTTPException(http_status.HTTP_409_CONFLICT, str(exc))
    if isinstance(exc, CasoJaArquivadoError):
        return HTTPException(http_status.HTTP_409_CONFLICT, str(exc))
    raise exc  # nao mapeado: propaga como erro interno


@router.post(
    "",
    response_model=CasoOut,
    status_code=http_status.HTTP_201_CREATED,
    summary="Criar caso (advogado autenticado)",
)
def criar_caso(
    dados: CasoCreate,
    _advogado: Usuario = Depends(require_advogado),
    service: CasoService = Depends(get_caso_service),
) -> Caso:
    """Cria um caso juridico (judicial, extrajudicial ou administrativo).

    `numero_processo` e opcional. O cliente precisa ser acessivel ao operador
    e, quando nao informado, o proprio operador assume a responsabilidade.
    """
    try:
        return service.criar(dados, _advogado)
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erros_caso(exc)


@router.get(
    "",
    response_model=CasoPaginaOut,
    summary="Listar casos (escopo do usuario autenticado)",
)
def listar_casos(
    q: str | None = Query(None, min_length=1, max_length=160),
    cliente_id: int | None = Query(None, gt=0),
    area: str | None = None,
    status: str | None = None,
    prioridade: str | None = None,
    responsavel_id: int | None = Query(None, gt=0),
    tipo_demanda: str | None = None,
    ordenar: str = Query("abertura", pattern="^(abertura|prioridade)$"),
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    _usuario: Usuario = Depends(get_current_user),
    service: CasoService = Depends(get_caso_service),
) -> CasoPaginaOut:
    """Admin ve todos; colaborador/funcionario veem os autorizados.

    Casos arquivados ficam fora desta listagem (use /arquivados).
    """
    return service.listar(
        _usuario,
        q=q,
        cliente_id=cliente_id,
        area=area,
        status=status,
        prioridade=prioridade,
        responsavel_id=responsavel_id,
        tipo_demanda=tipo_demanda,
        arquivado=False,
        ordenar=ordenar,
        pagina=pagina,
        limite=limite,
    )


# ATENCAO: declarada ANTES de /{caso_id} - caso contrario "arquivados" seria
# capturado como um id de caso e viraria 422.
@router.get(
    "/arquivados",
    response_model=CasoPaginaOut,
    summary="Listar casos arquivados (escopo do usuario)",
)
def listar_casos_arquivados(
    q: str | None = Query(None, min_length=1, max_length=160),
    cliente_id: int | None = Query(None, gt=0),
    area: str | None = None,
    status: str | None = None,
    prioridade: str | None = None,
    responsavel_id: int | None = Query(None, gt=0),
    tipo_demanda: str | None = None,
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    _usuario: Usuario = Depends(get_current_user),
    service: CasoService = Depends(get_caso_service),
) -> CasoPaginaOut:
    """Consulta de arquivados respeitando o escopo (admin: todos)."""
    return service.listar(
        _usuario,
        q=q,
        cliente_id=cliente_id,
        area=area,
        status=status,
        prioridade=prioridade,
        responsavel_id=responsavel_id,
        tipo_demanda=tipo_demanda,
        arquivado=True,
        ordenar="abertura",
        pagina=pagina,
        limite=limite,
    )


@router.get(
    "/{caso_id}",
    response_model=CasoOut,
    summary="Detalhe do caso (404 quando fora do escopo)",
)
def buscar_caso(
    caso_id: int,
    _usuario: Usuario = Depends(get_current_user),
    service: CasoService = Depends(get_caso_service),
) -> Caso:
    try:
        return service.buscar(caso_id, _usuario)
    except CasoNaoEncontradoError as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))


@router.patch(
    "/{caso_id}",
    response_model=CasoOut,
    summary="Atualizar dados gerais do caso (admin ou responsavel)",
)
def atualizar_caso(
    caso_id: int,
    dados: CasoUpdate,
    _usuario: Usuario = Depends(require_advogado),
    service: CasoService = Depends(get_caso_service),
) -> Caso:
    """Edicao restrita: admin ou advogado responsavel pelo caso.

    O payload nao aceita campos administrativos (`arquivado*`, `criado_por`)
    nem `cliente` (espelho) - extra="forbid" responde 422.
    """
    try:
        return service.atualizar(caso_id, dados, _usuario)
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erros_caso(exc)


@router.post(
    "/{caso_id}/arquivar",
    response_model=CasoOut,
    summary="Arquivar caso (Admin) - soft delete",
)
def arquivar_caso(
    caso_id: int,
    _admin: Usuario = Depends(require_admin),
    service: CasoService = Depends(get_caso_service),
) -> Caso:
    """Arquivamento logico: preserva historico, prazos, andamentos e acessos."""
    try:
        return service.arquivar(caso_id, _admin)
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erros_caso(exc)


@router.get(
    "/{caso_id}/historico",
    response_model=list[HistoricoOut],
    summary="Historico de alteracoes do caso (somente leitura)",
)
def historico_caso(
    caso_id: int,
    _usuario: Usuario = Depends(get_current_user),
    service: CasoService = Depends(get_caso_service),
) -> list[CasoHistorico]:
    """Auditoria do caso - visivel para quem tem acesso a ele (escopo Fase 1).

    Nao existe endpoint de escrita: o historico e gravado pelos services e nao
    pode ser alterado pela API.
    """
    try:
        return service.listar_historico(caso_id, _usuario)
    except CasoNaoEncontradoError as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))


@router.get(
    "/{caso_id}/usuarios",
    response_model=list[PermissaoCasoOut],
    summary="Usuarios com acesso ao caso (Admin)",
)
def listar_usuarios_do_caso(
    caso_id: int,
    incluir_revogados: bool = Query(
        False, description="Inclui tambem as concessoes revogadas (historico)"
    ),
    _admin: Usuario = Depends(require_admin),
    service: PermissaoCasoService = Depends(get_permissao_service),
) -> list[UsuarioCaso]:
    try:
        return service.listar_do_caso(
            caso_id, _admin, incluir_revogados=incluir_revogados
        )
    except CasoNaoEncontradoError as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))


@router.post(
    "/{caso_id}/usuarios",
    response_model=PermissaoCasoOut,
    status_code=http_status.HTTP_201_CREATED,
    summary="Conceder acesso de um usuario ao caso (Admin)",
)
def conceder_acesso(
    caso_id: int,
    dados: PermissaoCasoCreate,
    _admin: Usuario = Depends(require_admin),
    service: PermissaoCasoService = Depends(get_permissao_service),
) -> UsuarioCaso:
    try:
        return service.conceder(caso_id, dados, _admin)
    except CasoNaoEncontradoError as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))
    except UsuarioNaoEncontradoError as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))
    except AutoConcessaoNegadaError as exc:
        raise HTTPException(http_status.HTTP_403_FORBIDDEN, str(exc))
    except (DadosInvalidosError, DadosInvalidosUsuarioError) as exc:
        raise HTTPException(http_status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    except PermissaoJaExistenteError as exc:
        raise HTTPException(http_status.HTTP_409_CONFLICT, str(exc))


@router.delete(
    "/{caso_id}/usuarios/{usuario_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Revogar acesso de um usuario ao caso (Admin)",
)
def revogar_acesso(
    caso_id: int,
    usuario_id: int,
    _admin: Usuario = Depends(require_admin),
    service: PermissaoCasoService = Depends(get_permissao_service),
) -> Response:
    try:
        service.revogar(caso_id, usuario_id, _admin)
    except (CasoNaoEncontradoError, PermissaoNaoEncontradaError) as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
