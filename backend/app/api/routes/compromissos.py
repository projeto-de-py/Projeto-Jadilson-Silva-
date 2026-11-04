"""Compromissos de agenda (Fase 4).

Dois routers:
- `router` e montado em `/api/compromissos` e expoe cadastro, listagem com
  filtros, detalhe, atualizacao, status e historico;
- `router_agenda` e montado em `/api/agenda` e expoe o recorte temporal dos
  compromissos (periodo + responsavel) - a agenda NUNCA mistura prazos.

A autorizacao herda o escopo do caso (Fase 1); compromissos sem caso pertencem
somente ao administrador. A agenda exige autenticacao (sem acesso publico).
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status

from app.api.deps import (
    get_current_user,
    get_compromisso_service,
)
from app.core.tempo import hoje_brasilia
from app.models.compromisso_historico import CompromissoHistorico
from app.models.usuario import Usuario
from app.schemas.compromisso import (
    AgendaOut,
    CompromissoCreate,
    CompromissoOut,
    CompromissoPaginaOut,
    CompromissoStatusUpdate,
    CompromissoUpdate,
    HistoricoCompromissoOut,
    StatusCompromissoValor,
    TipoCompromissoValor,
)
from app.services.caso_service import (
    CasoNaoEncontradoError,
    ResponsavelInvalidoError,
)
from app.services.cliente_service import DadosInvalidosError
from app.services.compromisso_service import (
    CompromissoEstadoInvalidoError,
    CompromissoNaoEncontradoError,
    CompromissoSemPermissaoError,
    CompromissoService,
)

router = APIRouter()  # prefixo /api/compromissos
router_agenda = APIRouter()  # prefixo /api/agenda


def _mapear_erros_compromisso(exc: Exception) -> HTTPException:
    """Traduz erros de negocio do CompromissoService para HTTP."""
    if isinstance(exc, (CompromissoNaoEncontradoError, CasoNaoEncontradoError)):
        return HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, CompromissoSemPermissaoError):
        return HTTPException(http_status.HTTP_403_FORBIDDEN, str(exc))
    if isinstance(exc, (DadosInvalidosError, ResponsavelInvalidoError)):
        return HTTPException(http_status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    if isinstance(exc, CompromissoEstadoInvalidoError):
        return HTTPException(http_status.HTTP_409_CONFLICT, str(exc))
    raise exc  # nao mapeado: propaga como erro interno


# ------------------------------------------------------- /api/compromissos

@router.post(
    "",
    response_model=CompromissoOut,
    status_code=http_status.HTTP_201_CREATED,
    summary="Cadastrar compromisso",
)
def criar_compromisso(
    dados: CompromissoCreate,
    _usuario: Usuario = Depends(get_current_user),
    service: CompromissoService = Depends(get_compromisso_service),
) -> dict:
    """Compromisso com ou sem caso. Sem caso: apenas o administrador.

    `data_fim` deve ser posterior a `data_inicio` (horario local de Brasilia);
    com processo, o processo precisa pertencer ao mesmo caso.
    """
    try:
        return service.criar(dados, _usuario)
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erros_compromisso(exc)


@router.get(
    "",
    response_model=CompromissoPaginaOut,
    summary="Listar compromissos (escopo do usuario, paginado no banco)",
)
def listar_compromissos(
    q: str | None = Query(None, min_length=1, max_length=60, description="Titulo/descricao"),
    caso_id: int | None = Query(None, gt=0),
    processo_id: int | None = Query(None, gt=0),
    responsavel_id: int | None = Query(None, gt=0),
    tipo: TipoCompromissoValor | None = None,
    status_compromisso: StatusCompromissoValor | None = Query(
        None, alias="status", description="AGENDADO/REALIZADO/CANCELADO"
    ),
    inicio_de: date | None = None,
    inicio_ate: date | None = None,
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    _usuario: Usuario = Depends(get_current_user),
    service: CompromissoService = Depends(get_compromisso_service),
) -> dict:
    return service.listar(
        _usuario,
        q=q,
        caso_id=caso_id,
        processo_id=processo_id,
        responsavel_id=responsavel_id,
        tipo=tipo,
        status=status_compromisso,
        inicio_de=inicio_de,
        inicio_ate=inicio_ate,
        pagina=pagina,
        limite=limite,
    )


@router.get(
    "/{compromisso_id}",
    response_model=CompromissoOut,
    summary="Detalhe do compromisso (404 fora do escopo)",
)
def buscar_compromisso(
    compromisso_id: int,
    _usuario: Usuario = Depends(get_current_user),
    service: CompromissoService = Depends(get_compromisso_service),
) -> dict:
    try:
        return service.buscar(compromisso_id, _usuario)
    except CompromissoNaoEncontradoError as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))


@router.patch(
    "/{compromisso_id}",
    response_model=CompromissoOut,
    summary="Atualizar campos do compromisso",
)
def atualizar_compromisso(
    compromisso_id: int,
    dados: CompromissoUpdate,
    _usuario: Usuario = Depends(get_current_user),
    service: CompromissoService = Depends(get_compromisso_service),
) -> dict:
    try:
        return service.atualizar(compromisso_id, dados, _usuario)
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erros_compromisso(exc)


@router.patch(
    "/{compromisso_id}/status",
    response_model=CompromissoOut,
    summary="Alterar status (AGENDADO/REALIZADO/CANCELADO)",
)
def alterar_status_compromisso(
    compromisso_id: int,
    dados: CompromissoStatusUpdate,
    _usuario: Usuario = Depends(get_current_user),
    service: CompromissoService = Depends(get_compromisso_service),
) -> dict:
    try:
        return service.alterar_status(compromisso_id, dados, _usuario)
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erros_compromisso(exc)


@router.get(
    "/{compromisso_id}/historico",
    response_model=list[HistoricoCompromissoOut],
    summary="Historico de auditoria do compromisso (somente leitura)",
)
def listar_historico_compromisso(
    compromisso_id: int,
    _usuario: Usuario = Depends(get_current_user),
    service: CompromissoService = Depends(get_compromisso_service),
) -> list[CompromissoHistorico]:
    try:
        return service.listar_historico(compromisso_id, _usuario)
    except CompromissoNaoEncontradoError as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))


# ----------------------------------------------------------- /api/agenda

@router_agenda.get(
    "",
    response_model=AgendaOut,
    summary="Agenda de compromissos por periodo (sem prazos)",
)
def listar_agenda(
    de: date | None = Query(None, description="Inicio do periodo (padrao: hoje)"),
    ate: date | None = Query(None, description="Fim do periodo (padrao: inicio + 30 dias)"),
    responsavel_id: int | None = Query(None, gt=0),
    pagina: int = Query(1, ge=1),
    limite: int = Query(50, ge=1, le=100),
    _usuario: Usuario = Depends(get_current_user),
    service: CompromissoService = Depends(get_compromisso_service),
) -> dict:
    """Compromissos do periodo em ordem de horario (Brasilia).

    Compromissos sem caso aparecem apenas para o administrador; os demais
    respeitam o escopo dos casos. Prazos juridicos nunca entram aqui.
    """
    inicio = de or hoje_brasilia()
    fim = ate or (inicio + timedelta(days=30))
    try:
        return service.agenda(
            _usuario,
            de=inicio,
            ate=fim,
            responsavel_id=responsavel_id,
            pagina=pagina,
            limite=limite,
        )
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erros_compromisso(exc)
