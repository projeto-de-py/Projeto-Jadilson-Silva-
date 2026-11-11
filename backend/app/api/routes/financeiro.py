"""Financeiro: cobranca de honorarios (Asaas). Somente o advogado principal opera."""

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.api.erros_integracao import http_de_integracao
from app.database import get_db
from app.models.usuario import Usuario
from app.repositories.caso_repository import CasoRepository
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.cobranca_repository import CobrancaRepository
from app.repositories.evento_webhook_repository import EventoWebhookRepository
from app.schemas.financeiro import CobrancaCreate, CobrancaOut, ResumoFinanceiroOut
from app.services.asaas import AsaasService
from app.services.financeiro_service import (
    CobrancaDadosInvalidosError,
    FinanceiroService,
    RegistroNaoEncontradoError,
)
from app.integrations.erros import IntegracaoErro

router = APIRouter()


def get_financeiro_service(db: Session = Depends(get_db)) -> FinanceiroService:
    return FinanceiroService(
        cobrancas=CobrancaRepository(db),
        clientes=ClienteRepository(db),
        casos=CasoRepository(db),
        eventos=EventoWebhookRepository(db),
        asaas=AsaasService.do_ambiente(),
    )


@router.post(
    "/cobrancas",
    response_model=list[CobrancaOut],
    status_code=http_status.HTTP_201_CREATED,
    summary="Emitir cobranca Pix ou boleto, avulsa ou parcelada (Admin)",
)
def emitir_cobranca(
    dados: CobrancaCreate,
    admin: Usuario = Depends(require_admin),
    servico: FinanceiroService = Depends(get_financeiro_service),
):
    try:
        return servico.emitir(dados, admin)
    except RegistroNaoEncontradoError as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))
    except CobrancaDadosInvalidosError as exc:
        raise HTTPException(http_status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc))
    except IntegracaoErro as exc:
        raise http_de_integracao(exc)


@router.get("/cobrancas", response_model=list[CobrancaOut], summary="Listar cobrancas (Admin)")
def listar_cobrancas(
    cliente_id: int | None = Query(None, ge=1),
    status: str | None = Query(None, pattern="^(PENDENTE|RECEBIDA|VENCIDA|CANCELADA)$"),
    limite: int = Query(50, ge=1, le=200),
    _admin: Usuario = Depends(require_admin),
    servico: FinanceiroService = Depends(get_financeiro_service),
):
    return servico.cobrancas.listar(cliente_id=cliente_id, status=status, limite=limite)


@router.get(
    "/clientes/{cliente_id}/resumo",
    response_model=ResumoFinanceiroOut,
    summary="Situacao financeira do cliente (Admin)",
)
def resumo_do_cliente(
    cliente_id: int,
    _admin: Usuario = Depends(require_admin),
    servico: FinanceiroService = Depends(get_financeiro_service),
):
    try:
        return servico.resumo(cliente_id)
    except RegistroNaoEncontradoError as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))
