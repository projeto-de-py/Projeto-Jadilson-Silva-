"""Consulta dos prazos urgentes (vencidos ou nos proximos sete dias)."""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.database import get_db
from app.models.caso import Caso
from app.models.prazo import Prazo
from app.models.usuario import Usuario

router = APIRouter()


@router.get("/urgentes")
def listar_prazos_urgentes(dias: int = Query(7, ge=0, le=90), pagina: int = Query(1, ge=1),
                           limite: int = Query(20, ge=1, le=100), _usuario: Usuario = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    filtros = (Prazo.cumprido.is_(False), Prazo.data_limite <= date.today() + timedelta(days=dias))
    total = db.scalar(select(func.count()).select_from(Prazo).where(*filtros)) or 0
    rows = db.execute(select(Prazo, Caso.numero_processo, Caso.cliente).join(Caso).where(*filtros)
                      .order_by(Prazo.data_limite, Prazo.id).offset((pagina - 1) * limite).limit(limite)).all()
    itens = [{"id": p.id, "caso_id": p.caso_id, "titulo": p.titulo, "tipo": p.tipo,
              "data_limite": p.data_limite, "cumprido": p.cumprido,
              "numero_processo": numero, "cliente": cliente} for p, numero, cliente in rows]
    return {"itens": itens, "total": total, "pagina": pagina, "limite": limite}
