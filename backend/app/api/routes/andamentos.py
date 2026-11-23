"""Andamentos do caso: historico registrado a mao ou importado do tribunal (DataJud).

Rotas montadas sob /casos/{caso_id}/andamentos. O acesso segue o escopo do caso (404 fora dele).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_caso_service, get_current_user
from app.api.erros_integracao import http_de_integracao
from app.api.routes.consultas import get_processo_service, limitar_consultas
from app.database import get_db
from app.integrations.erros import IntegracaoErro
from app.models.usuario import Usuario
from app.repositories.andamento_repository import AndamentoRepository
from app.schemas.andamento import AndamentoCreate, AndamentoOut, SincronizacaoOut
from app.services.andamento_service import (
    AndamentoDoTribunalError,
    AndamentoNaoEncontradoError,
    AndamentoService,
    CasoSemNumeroError,
)
from app.services.caso_service import CasoNaoEncontradoError, CasoService
from app.services.processo_externo_service import ProcessoExternoService

router = APIRouter()


def get_andamento_service(
    db: Session = Depends(get_db),
    casos: CasoService = Depends(get_caso_service),
    processos: ProcessoExternoService = Depends(get_processo_service),
) -> AndamentoService:
    return AndamentoService(casos=casos, andamentos=AndamentoRepository(db), processos=processos)


@router.get("/{caso_id}/andamentos", response_model=list[AndamentoOut], summary="Andamentos do caso")
def listar_andamentos(
    caso_id: int,
    limite: int = Query(200, ge=1, le=500),
    usuario: Usuario = Depends(get_current_user),
    servico: AndamentoService = Depends(get_andamento_service),
):
    try:
        return servico.listar(caso_id, usuario, limite)
    except CasoNaoEncontradoError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))


@router.post("/{caso_id}/andamentos", response_model=AndamentoOut, status_code=status.HTTP_201_CREATED, summary="Registrar andamento")
def criar_andamento(
    caso_id: int,
    dados: AndamentoCreate,
    usuario: Usuario = Depends(get_current_user),
    servico: AndamentoService = Depends(get_andamento_service),
):
    try:
        return servico.criar(caso_id, dados, usuario)
    except CasoNaoEncontradoError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))


@router.post("/{caso_id}/andamentos/sincronizar", response_model=SincronizacaoOut, summary="Importar andamentos do tribunal (DataJud)")
def sincronizar_andamentos(
    caso_id: int,
    usuario: Usuario = Depends(limitar_consultas),
    servico: AndamentoService = Depends(get_andamento_service),
):
    try:
        resultado = servico.sincronizar(caso_id, usuario)
    except CasoNaoEncontradoError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    except CasoSemNumeroError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc))
    except IntegracaoErro as exc:
        raise http_de_integracao(exc)
    return SincronizacaoOut(
        numero=resultado.numero,
        tribunal=resultado.tribunal,
        encontrado=resultado.encontrado,
        novos=resultado.novos,
        ja_existentes=resultado.ja_existentes,
        mensagem=resultado.mensagem,
    )


@router.delete("/{caso_id}/andamentos/{andamento_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Apagar andamento registrado a mao")
def excluir_andamento(
    caso_id: int,
    andamento_id: int,
    usuario: Usuario = Depends(get_current_user),
    servico: AndamentoService = Depends(get_andamento_service),
):
    try:
        servico.excluir(caso_id, andamento_id, usuario)
    except (CasoNaoEncontradoError, AndamentoNaoEncontradoError) as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    except AndamentoDoTribunalError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
