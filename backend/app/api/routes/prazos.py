"""Gerenciamento de prazos (Fase 4).

Rota unica `/api/prazos`: cadastro, listagem com filtros e paginacao no
banco, detalhe, atualizacao, transicoes (concluir/reabrir/cancelar),
historico (somente leitura) e o endpoint de urgentes aprimorado - vencidos,
que vencem hoje e os proximos N dias, em horario local de Brasilia.

A autorizacao de leitura herda o escopo do caso (Fase 1): prazo fora do
escopo responde 404, nunca revelando a existencia de casos alheios. A
escrita exige admin, responsavel do caso ou a concessao `pode_gerenciar_prazos`
(403). O historico nao possui nenhuma rota de escrita.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status

from app.api.deps import (
    get_current_user,
    get_prazo_service,
)
from app.models.prazo_historico import PrazoHistorico
from app.models.usuario import Usuario
from app.schemas.prazo import (
    HistoricoPrazoOut,
    PrazoCreate,
    PrazoOut,
    PrazoPaginaOut,
    PrazoUrgentePaginaOut,
    PrazoUpdate,
    PrioridadeValor,
    StatusPrazoValor,
    TipoPrazoValor,
)
from app.services.caso_service import (
    CasoNaoEncontradoError,
    ResponsavelInvalidoError,
)
from app.services.cliente_service import DadosInvalidosError
from app.services.prazo_service import (
    PrazoEstadoInvalidoError,
    PrazoNaoEncontradoError,
    PrazoSemPermissaoError,
    PrazoService,
)

router = APIRouter()


def _mapear_erros_prazo(exc: Exception) -> HTTPException:
    """Traduz erros de negocio do PrazoService para HTTP."""
    if isinstance(exc, (PrazoNaoEncontradoError, CasoNaoEncontradoError)):
        return HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, PrazoSemPermissaoError):
        return HTTPException(http_status.HTTP_403_FORBIDDEN, str(exc))
    if isinstance(exc, (DadosInvalidosError, ResponsavelInvalidoError)):
        return HTTPException(http_status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    if isinstance(exc, PrazoEstadoInvalidoError):
        return HTTPException(http_status.HTTP_409_CONFLICT, str(exc))
    raise exc  # nao mapeado: propaga como erro interno


# ------------------------------------------------------------ urgentes
# Declarado antes de "/{prazo_id}" para "urgentes" nao ser lido como id.

@router.get(
    "/urgentes",
    response_model=PrazoUrgentePaginaOut,
    summary="Prazos urgentes (vencidos, hoje e proximos dias)",
)
def listar_prazos_urgentes(
    dias: int = Query(7, ge=0, le=90, description="Horizonte maximo de 90 dias"),
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    _usuario: Usuario = Depends(get_current_user),
    service: PrazoService = Depends(get_prazo_service),
) -> dict:
    """Vencidos + vencem hoje + vencem nos proximos `dias` (Brasilia).

    Somente prazos em aberto (PENDENTE/EM_ANDAMENTO) do escopo do usuario;
    ordenados por situacao, prioridade e data.
    """
    try:
        return service.listar_urgentes(_usuario, dias=dias, pagina=pagina, limite=limite)
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erros_prazo(exc)


# --------------------------------------------------------------- CRUD

@router.post(
    "",
    response_model=PrazoOut,
    status_code=http_status.HTTP_201_CREATED,
    summary="Cadastrar prazo no caso",
)
def criar_prazo(
    dados: PrazoCreate,
    _usuario: Usuario = Depends(get_current_user),
    service: PrazoService = Depends(get_prazo_service),
) -> dict:
    """Cria um prazo com data informada manualmente (sem calculo automatico).

    Exige permissao de escrita no caso (admin, responsavel ou a concessao
    `pode_gerenciar_prazos`); o responsavel ausente vem a ser o operador.
    """
    try:
        return service.criar(dados, _usuario)
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erros_prazo(exc)


@router.get(
    "",
    response_model=PrazoPaginaOut,
    summary="Listar prazos (escopo do usuario, paginado no banco)",
)
def listar_prazos(
    q: str | None = Query(None, min_length=1, max_length=60, description="Titulo/descricao"),
    caso_id: int | None = Query(None, gt=0),
    processo_id: int | None = Query(None, gt=0),
    responsavel_id: int | None = Query(None, gt=0),
    tipo: TipoPrazoValor | None = Query(None, description="Categoria do prazo"),
    status_prazo: StatusPrazoValor | None = Query(
        None, alias="status", description="PENDENTE/EM_ANDAMENTO/CONCLUIDO/CANCELADO"
    ),
    prioridade: PrioridadeValor | None = Query(None, description="BAIXA/MEDIA/ALTA/URGENTE"),
    vencimento_de: date | None = None,
    vencimento_ate: date | None = None,
    vencidos: bool | None = Query(None, description="Somente vencidos (true) ou nao vencidos (false)"),
    pendentes: bool | None = Query(
        None,
        description="Em aberto (true) = PENDENTE ou EM_ANDAMENTO; "
        "false = CONCLUIDO ou CANCELADO",
    ),
    concluidos: bool | None = Query(None, description="Somente concluidos (true) ou nao concluidos (false)"),
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    _usuario: Usuario = Depends(get_current_user),
    service: PrazoService = Depends(get_prazo_service),
) -> dict:
    """Admin ve todos; demais veem apenas prazos de casos autorizados."""
    return service.listar(
        _usuario,
        q=q,
        caso_id=caso_id,
        processo_id=processo_id,
        responsavel_id=responsavel_id,
        tipo=tipo,
        status=status_prazo,
        prioridade=prioridade,
        vencimento_de=vencimento_de,
        vencimento_ate=vencimento_ate,
        vencidos=vencidos,
        pendentes=pendentes,
        concluidos=concluidos,
        pagina=pagina,
        limite=limite,
    )


@router.get(
    "/{prazo_id}",
    response_model=PrazoOut,
    summary="Detalhe do prazo (404 fora do escopo)",
)
def buscar_prazo(
    prazo_id: int,
    _usuario: Usuario = Depends(get_current_user),
    service: PrazoService = Depends(get_prazo_service),
) -> dict:
    try:
        return service.buscar(prazo_id, _usuario)
    except PrazoNaoEncontradoError as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))


@router.patch(
    "/{prazo_id}",
    response_model=PrazoOut,
    summary="Atualizar campos do prazo",
)
def atualizar_prazo(
    prazo_id: int,
    dados: PrazoUpdate,
    _usuario: Usuario = Depends(get_current_user),
    service: PrazoService = Depends(get_prazo_service),
) -> dict:
    """PATCH parcial: status final (CONCLUIDO/CANCELADO) exige as rotas proprias."""
    try:
        return service.atualizar(prazo_id, dados, _usuario)
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erros_prazo(exc)


@router.patch(
    "/{prazo_id}/concluir",
    response_model=PrazoOut,
    summary="Concluir prazo (registra data, hora e usuario)",
)
def concluir_prazo(
    prazo_id: int,
    _usuario: Usuario = Depends(get_current_user),
    service: PrazoService = Depends(get_prazo_service),
) -> dict:
    try:
        return service.concluir(prazo_id, _usuario)
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erros_prazo(exc)


@router.patch(
    "/{prazo_id}/reabrir",
    response_model=PrazoOut,
    summary="Reabrir prazo concluido/cancelado (preserva o historico)",
)
def reabrir_prazo(
    prazo_id: int,
    _usuario: Usuario = Depends(get_current_user),
    service: PrazoService = Depends(get_prazo_service),
) -> dict:
    try:
        return service.reabrir(prazo_id, _usuario)
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erros_prazo(exc)


@router.patch(
    "/{prazo_id}/cancelar",
    response_model=PrazoOut,
    summary="Cancelar prazo em aberto",
)
def cancelar_prazo(
    prazo_id: int,
    _usuario: Usuario = Depends(get_current_user),
    service: PrazoService = Depends(get_prazo_service),
) -> dict:
    try:
        return service.cancelar(prazo_id, _usuario)
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erros_prazo(exc)


@router.get(
    "/{prazo_id}/historico",
    response_model=list[HistoricoPrazoOut],
    summary="Historico de auditoria do prazo (somente leitura)",
)
def listar_historico_prazo(
    prazo_id: int,
    _usuario: Usuario = Depends(get_current_user),
    service: PrazoService = Depends(get_prazo_service),
) -> list[PrazoHistorico]:
    try:
        return service.listar_historico(prazo_id, _usuario)
    except PrazoNaoEncontradoError as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))
