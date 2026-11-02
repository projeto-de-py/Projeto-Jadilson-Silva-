"""Assinatura eletronica (ZapSign). Somente o advogado principal envia e consulta."""

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.database import get_db
from app.models.usuario import Usuario
from app.repositories.assinatura_repository import AssinaturaRepository
from app.repositories.caso_repository import CasoRepository
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.evento_webhook_repository import EventoWebhookRepository
from app.schemas.assinatura import AssinaturaCreate, AssinaturaOut
from app.services.assinatura_service import (
    AssinaturaDadosInvalidosError,
    AssinaturaService,
    RegistroNaoEncontradoError,
)
from app.api.erros_integracao import http_de_integracao
from app.integrations.erros import IntegracaoErro
from app.services.zapsign import ZapSignService

router = APIRouter()


def get_assinatura_service(db: Session = Depends(get_db)) -> AssinaturaService:
    return AssinaturaService(
        assinaturas=AssinaturaRepository(db),
        clientes=ClienteRepository(db),
        casos=CasoRepository(db),
        eventos=EventoWebhookRepository(db),
        zapsign=ZapSignService.do_ambiente(),
    )


@router.post(
    "",
    response_model=AssinaturaOut,
    status_code=http_status.HTTP_201_CREATED,
    summary="Enviar PDF para assinatura (Admin)",
)
def enviar_para_assinatura(
    dados: AssinaturaCreate,
    admin: Usuario = Depends(require_admin),
    servico: AssinaturaService = Depends(get_assinatura_service),
):
    try:
        return servico.enviar(dados, admin)
    except RegistroNaoEncontradoError as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))
    except AssinaturaDadosInvalidosError as exc:
        raise HTTPException(http_status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc))
    except IntegracaoErro as exc:
        raise http_de_integracao(exc)


@router.get("", response_model=list[AssinaturaOut], summary="Listar assinaturas (Admin)")
def listar_assinaturas(
    cliente_id: int | None = Query(None, ge=1),
    status: str | None = Query(None, pattern="^(ENVIADO|ASSINADO|RECUSADO|ERRO)$"),
    limite: int = Query(50, ge=1, le=200),
    _admin: Usuario = Depends(require_admin),
    servico: AssinaturaService = Depends(get_assinatura_service),
):
    return servico.assinaturas.listar(cliente_id=cliente_id, status=status, limite=limite)


@router.get("/{assinatura_id}", response_model=AssinaturaOut, summary="Detalhe da assinatura (Admin)")
def obter_assinatura(
    assinatura_id: int,
    _admin: Usuario = Depends(require_admin),
    servico: AssinaturaService = Depends(get_assinatura_service),
):
    a = servico.assinaturas.buscar_por_id(assinatura_id)
    if a is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Assinatura nao encontrada")
    return a
