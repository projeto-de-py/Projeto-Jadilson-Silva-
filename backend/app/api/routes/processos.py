"""Gerenciamento de processos judiciais (Fase 3).

Dois routers:
- `router_caso` e montado em `/api/casos` e expoe o sub-recurso
  `/{caso_id}/processos` (cadastro/listagem por caso);
- `router` e montado em `/api/processos` e expoe consulta geral, detalhe,
  atualizacao, status, arquivamento e historico.

A autorizacao de leitura herda o escopo do caso (Fase 1): processo fora do
escopo responde 404, nunca revelando a existencia de casos alheios.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status

from app.api.deps import (
    get_current_user,
    get_processo_service,
)
from app.models.processo_historico import ProcessoHistorico
from app.models.processo_judicial import ProcessoJudicial
from app.models.usuario import Usuario
from app.schemas.processo import (
    HistoricoProcessoOut,
    ProcessoCreate,
    ProcessoOut,
    ProcessoPaginaOut,
    ProcessoStatusUpdate,
    ProcessoUpdate,
)
from app.services.caso_service import CasoNaoEncontradoError
from app.services.cliente_service import DadosInvalidosError
from app.services.processo_service import (
    ProcessoJaArquivadoError,
    ProcessoJudicialService,
    ProcessoNaoEncontradoError,
    ProcessoNumeroDuplicadoError,
    ProcessoSemPermissaoError,
)
from app.services.usuario_service import (
    DadosInvalidosError as DadosInvalidosUsuarioError,
)

router_caso = APIRouter()  # prefixo /api/casos
router = APIRouter()  # prefixo /api/processos


def _mapear_erros_processo(exc: Exception) -> HTTPException:
    """Traduz erros de negocio do ProcessoJudicialService para HTTP."""
    if isinstance(exc, (ProcessoNaoEncontradoError, CasoNaoEncontradoError)):
        return HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, ProcessoSemPermissaoError):
        return HTTPException(http_status.HTTP_403_FORBIDDEN, str(exc))
    if isinstance(exc, (DadosInvalidosError, DadosInvalidosUsuarioError)):
        return HTTPException(http_status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    if isinstance(
        exc, (ProcessoNumeroDuplicadoError, ProcessoJaArquivadoError)
    ):
        return HTTPException(http_status.HTTP_409_CONFLICT, str(exc))
    raise exc  # nao mapeado: propaga como erro interno


# ------------------------------------------------------- por caso (/api/casos)

@router_caso.post(
    "/{caso_id}/processos",
    response_model=ProcessoOut,
    status_code=http_status.HTTP_201_CREATED,
    summary="Cadastrar processo judicial no caso",
)
def criar_processo(
    caso_id: int,
    dados: ProcessoCreate,
    _usuario: Usuario = Depends(get_current_user),
    service: ProcessoJudicialService = Depends(get_processo_service),
) -> ProcessoJudicial:
    """Vincula um processo CNJ a um caso acessivel ao operador.

    Exige permissao de escrita no caso (admin, responsavel ou a concessao
    `pode_gerenciar_processos`) - funcionario sem concessao leva 403.
    """
    try:
        return service.criar(caso_id, dados, _usuario)
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erros_processo(exc)


@router_caso.get(
    "/{caso_id}/processos",
    response_model=list[ProcessoOut],
    summary="Processos de um caso (escopo do usuario)",
)
def listar_processos_do_caso(
    caso_id: int,
    incluir_arquivados: bool = Query(False, description="Inclui processos arquivados"),
    _usuario: Usuario = Depends(get_current_user),
    service: ProcessoJudicialService = Depends(get_processo_service),
) -> list[ProcessoJudicial]:
    try:
        return service.listar_do_caso(
            caso_id, _usuario, arquivados=incluir_arquivados
        )
    except CasoNaoEncontradoError as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))


# ------------------------------------------------------------ /api/processos

@router.get(
    "",
    response_model=ProcessoPaginaOut,
    summary="Listar processos (escopo do usuario, paginado no banco)",
)
def listar_processos(
    q: str | None = Query(None, min_length=1, max_length=40, description="Numero CNJ"),
    caso_id: int | None = Query(None, gt=0),
    tribunal: str | None = None,
    comarca: str | None = None,
    instancia: str | None = None,
    classe_processual: str | None = None,
    status: str | None = None,
    distribuicao_de: date | None = None,
    distribuicao_ate: date | None = None,
    arquivados: bool = Query(False, description="Lista os arquivados em vez dos ativos"),
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    _usuario: Usuario = Depends(get_current_user),
    service: ProcessoJudicialService = Depends(get_processo_service),
) -> ProcessoPaginaOut:
    """Admin ve todos; demais veem apenas processos de casos autorizados."""
    return service.listar(
        _usuario,
        q=q,
        caso_id=caso_id,
        tribunal=tribunal,
        comarca=comarca,
        instancia=instancia,
        classe_processual=classe_processual,
        status=status,
        distribuicao_de=distribuicao_de,
        distribuicao_ate=distribuicao_ate,
        arquivado=arquivados,
        pagina=pagina,
        limite=limite,
    )


@router.get(
    "/{processo_id}",
    response_model=ProcessoOut,
    summary="Detalhe do processo (404 fora do escopo)",
)
def buscar_processo(
    processo_id: int,
    _usuario: Usuario = Depends(get_current_user),
    service: ProcessoJudicialService = Depends(get_processo_service),
) -> ProcessoJudicial:
    try:
        return service.buscar(processo_id, _usuario)
    except ProcessoNaoEncontradoError as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))


@router.patch(
    "/{processo_id}",
    response_model=ProcessoOut,
    summary="Atualizar dados do processo (escrita no caso)",
)
def atualizar_processo(
    processo_id: int,
    dados: ProcessoUpdate,
    _usuario: Usuario = Depends(get_current_user),
    service: ProcessoJudicialService = Depends(get_processo_service),
) -> ProcessoJudicial:
    """`caso_id` e `criado_por` nao sao aceitos no payload (extra=forbid)."""
    try:
        return service.atualizar(processo_id, dados, _usuario)
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erros_processo(exc)


@router.patch(
    "/{processo_id}/status",
    response_model=ProcessoOut,
    summary="Mudar situacao do processo (encerramento = BAIXADO/EXTINTO)",
)
def mudar_status_processo(
    processo_id: int,
    dados: ProcessoStatusUpdate,
    _usuario: Usuario = Depends(get_current_user),
    service: ProcessoJudicialService = Depends(get_processo_service),
) -> ProcessoJudicial:
    try:
        return service.mudar_status(processo_id, dados, _usuario)
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erros_processo(exc)


@router.post(
    "/{processo_id}/arquivar",
    response_model=ProcessoOut,
    summary="Arquivar processo (soft delete - distinto do caso)",
)
def arquivar_processo(
    processo_id: int,
    _usuario: Usuario = Depends(get_current_user),
    service: ProcessoJudicialService = Depends(get_processo_service),
) -> ProcessoJudicial:
    """Arquivamento do PROCESSO: o caso pode continuar ativo."""
    try:
        return service.arquivar(processo_id, _usuario)
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erros_processo(exc)


@router.get(
    "/{processo_id}/historico",
    response_model=list[HistoricoProcessoOut],
    summary="Historico de alteracoes do processo (somente leitura)",
)
def historico_processo(
    processo_id: int,
    _usuario: Usuario = Depends(get_current_user),
    service: ProcessoJudicialService = Depends(get_processo_service),
) -> list[ProcessoHistorico]:
    try:
        return service.listar_historico(processo_id, _usuario)
    except ProcessoNaoEncontradoError as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))
