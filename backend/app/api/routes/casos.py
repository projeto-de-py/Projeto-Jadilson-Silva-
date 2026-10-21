"""Consulta e busca paginada de processos."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select, func
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.database import get_db
from app.models.caso import Caso
from app.models.usuario import Usuario

router = APIRouter()


@router.get("")
def listar_casos(q: str | None = Query(None, min_length=1, max_length=160), status: str | None = None,
                 pagina: int = Query(1, ge=1), limite: int = Query(20, ge=1, le=100),
                 _usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    filtros = []
    if q:
        termo = f"%{q.strip()}%"
        filtros.append(or_(Caso.numero_processo.ilike(termo), Caso.cliente.ilike(termo), Caso.parte_contraria.ilike(termo)))
    if status:
        filtros.append(Caso.status == status)
    total = db.scalar(select(func.count()).select_from(Caso).where(*filtros)) or 0
    itens = db.scalars(select(Caso).where(*filtros).order_by(Caso.criado_em.desc(), Caso.id.desc()).offset((pagina - 1) * limite).limit(limite)).all()
    return {"itens": itens, "total": total, "pagina": pagina, "limite": limite}
