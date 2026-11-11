"""Endpoints da IA do escritorio.

Seguranca:
- exige sessao (cookie) e, por ser POST, o token CSRF (middleware em main.py);
- limite de uso por usuario (janela deslizante) para controlar custo e abuso;
- `caso_id` passa pelo MESMO escopo de visibilidade dos casos (404 se fora dele);
- o servidor nunca devolve o texto dos prompts, so o inventario (nome e versao).
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_caso_service, get_current_user, require_admin
from app.config import get_settings
from app.database import get_db
from app.ia import carregador
from app.ia.provedores import obter_provedor
from app.ia.schemas import (
    CompletarRequest,
    CompletarResponse,
    ControleIAResponse,
    SugerirRequest,
    SugerirResponse,
)
from app.ia.servico import IABloqueadaError, IAIndisponivelError, IAServico
from app.models.usuario import Usuario
from app.repositories.uso_ia_repository import UsoIARepository
from app.services.caso_service import CasoNaoEncontradoError, CasoService

router = APIRouter()
settings = get_settings()


def get_ia_servico(db: Session = Depends(get_db)) -> IAServico:
    return IAServico(provedor=obter_provedor(settings.ia_provedor), uso=UsoIARepository(db))


def _limitar(request: Request, usuario: Usuario, prefixo: str, limite: int, janela: int) -> None:
    request.app.state.limiter.check(f"{prefixo}:{usuario.id}", limite, janela)


def _caso_do_escopo(casos: CasoService, caso_id: int | None, usuario: Usuario):
    if caso_id is None:
        return None
    try:
        return casos.buscar(caso_id, usuario)
    except CasoNaoEncontradoError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))


@router.post("/sugerir", response_model=SugerirResponse, summary="Sugestoes da IA para o documento")
def sugerir(
    dados: SugerirRequest,
    request: Request,
    usuario: Usuario = Depends(get_current_user),
    servico: IAServico = Depends(get_ia_servico),
    casos: CasoService = Depends(get_caso_service),
) -> SugerirResponse:
    _limitar(request, usuario, "ia", settings.ia_limite_sugerir_hora, 3600)
    caso = _caso_do_escopo(casos, dados.caso_id, usuario)
    try:
        return servico.sugerir(dados, usuario, caso)
    except IABloqueadaError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc))
    except IAIndisponivelError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))


@router.post("/completar", response_model=CompletarResponse, summary="Continuacao de texto (autocompletar)")
def completar(
    dados: CompletarRequest,
    request: Request,
    usuario: Usuario = Depends(get_current_user),
    servico: IAServico = Depends(get_ia_servico),
    casos: CasoService = Depends(get_caso_service),
) -> CompletarResponse:
    _limitar(request, usuario, "ia-c", settings.ia_limite_completar_minuto, 60)
    caso = _caso_do_escopo(casos, dados.caso_id, usuario)
    try:
        return servico.completar(dados, usuario, caso)
    except IAIndisponivelError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))


@router.get("/controle", response_model=ControleIAResponse, summary="Arquivos de controle da IA (admin)")
def controle(_admin: Usuario = Depends(require_admin)) -> ControleIAResponse:
    """Inventario da pasta de controle: nome, tamanho e versao de cada perfil e tarefa."""
    provedor = obter_provedor(settings.ia_provedor)
    inv = carregador.inventario()
    return ControleIAResponse(provedor=provedor.nome, simulado=provedor.simulado, **inv)
