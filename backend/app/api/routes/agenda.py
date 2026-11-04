"""Eventos compartilhados da agenda."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.evento_agenda import EventoAgenda
from app.models.usuario import Usuario
from app.repositories.notificacao_repository import NotificacaoRepository
from app.schemas.evento_agenda import (
    ContribuidorAgendaOut,
    EventoAgendaCreate,
    EventoAgendaOut,
)
from app.services.notificacao_service import GeradorNotificacaoAudiencia

router = APIRouter()


@router.get("/contribuidores", response_model=list[ContribuidorAgendaOut])
def listar_contribuidores(
    _usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[dict]:
    usuarios = db.scalars(
        select(Usuario).where(Usuario.ativo.is_(True)).order_by(Usuario.nome)
    ).all()
    return [{"id": usuario.id, "nome": usuario.nome} for usuario in usuarios]


@router.get("/eventos", response_model=list[EventoAgendaOut])
def listar_eventos(
    usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[EventoAgenda]:
    stmt = (
        select(EventoAgenda)
        .where(
            or_(
                EventoAgenda.destinatario_id.is_(None),
                EventoAgenda.destinatario_id == usuario.id,
                EventoAgenda.criado_por_id == usuario.id,
            )
        )
        .order_by(EventoAgenda.inicio)
    )
    return list(db.scalars(stmt))


@router.post("/eventos", response_model=EventoAgendaOut, status_code=status.HTTP_201_CREATED)
def criar_evento(
    dados: EventoAgendaCreate,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EventoAgenda:
    destinatario: Usuario | None = None
    if dados.destinatario_id is not None:
        destinatario = db.get(Usuario, dados.destinatario_id)
        if destinatario is None or not destinatario.ativo:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Contribuidor inválido ou inativo")
    evento = EventoAgenda(**dados.model_dump(), criado_por_id=usuario.id)
    db.add(evento)
    db.commit()
    db.refresh(evento)
    gerador = GeradorNotificacaoAudiencia(NotificacaoRepository(db))
    gerador.gerar_para(usuario)
    if destinatario is not None and destinatario.id != usuario.id:
        gerador.gerar_para(destinatario)
    return evento


@router.delete("/eventos/{evento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_evento(
    evento_id: int,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    evento = db.get(EventoAgenda, evento_id)
    if evento is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evento não encontrado")
    if evento.criado_por_id != usuario.id and not usuario.administrador:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Somente quem criou o evento ou o administrador pode excluí-lo")
    db.delete(evento)
    db.commit()
