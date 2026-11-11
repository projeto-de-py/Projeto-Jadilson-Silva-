"""Endpoints pessoais de notificações; IDs são sempre limitados ao usuário."""

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.usuario import Usuario
from app.repositories.notificacao_repository import NotificacaoRepository
from app.schemas.notificacao import (
    ContagemNotificacaoOut,
    NotificacaoOut,
    NotificacaoPaginaOut,
    TesteNotificacaoIn,
    TesteNotificacaoOut,
)
from app.services.notificacao_service import (
    NotificacaoService,
    sincronizar_notificacoes_automaticas,
)

router = APIRouter()


def _service(db: Session) -> NotificacaoService:
    return NotificacaoService(NotificacaoRepository(db))


@router.get("", response_model=NotificacaoPaginaOut)
def listar(
    pagina: int = Query(1, ge=1), limite: int = Query(20, ge=1, le=100),
    lidas: bool | None = Query(None), usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    repo = NotificacaoRepository(db)
    sincronizar_notificacoes_automaticas(repo, usuario)
    return _service(db).listar(usuario.id, pagina=pagina, limite=limite, lidas=lidas)


@router.get("/nao-lidas/contagem", response_model=ContagemNotificacaoOut)
def contar(usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    sincronizar_notificacoes_automaticas(NotificacaoRepository(db), usuario)
    return {"nao_lidas": _service(db).contar_nao_lidas(usuario.id)}


@router.post("/testar", response_model=TesteNotificacaoOut, status_code=status.HTTP_201_CREATED)
def testar_notificacao(
    dados: TesteNotificacaoIn | None = Body(default=None),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    tipos: list[str] | None = None
    if dados is not None:
        if dados.tipos:
            tipos = list(dados.tipos)
        elif dados.tipo:
            tipos = [dados.tipo]
    itens = _service(db).emitir_teste(usuario.id, tipos=tipos)
    return {"criadas": len(itens), "itens": itens}


@router.post("/lidas")
def marcar_todas(usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"marcadas": _service(db).marcar_todas_lidas(usuario.id)}


@router.delete("")
@router.post("/limpar")
def limpar_todas(usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"removidas": _service(db).limpar_todas(usuario.id)}


@router.post("/{notificacao_id}/lida", response_model=NotificacaoOut)
def marcar_lida(notificacao_id: int, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    item = _service(db).marcar_lida(usuario.id, notificacao_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notificação não encontrada")
    return item
