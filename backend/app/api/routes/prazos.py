"""Consulta dos prazos urgentes (vencidos ou nos proximos N dias)."""
from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_prazo_repo
from app.models.usuario import Usuario
from app.repositories.prazo_repository import PrazoRepository
from app.services.prazo_service import PrazoService

router = APIRouter()


@router.get("/urgentes", summary="Prazos urgentes do escopo do usuario")
def listar_prazos_urgentes(
    dias: int = Query(7, ge=0, le=90),
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    _usuario: Usuario = Depends(get_current_user),
    repo: PrazoRepository = Depends(get_prazo_repo),
) -> dict:
    """Somente prazos de casos que o usuario pode acessar (RF03 no servidor)."""
    return PrazoService(repo).listar_urgentes(
        _usuario, dias=dias, pagina=pagina, limite=limite
    )
