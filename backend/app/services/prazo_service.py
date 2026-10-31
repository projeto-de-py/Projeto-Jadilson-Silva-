"""Service Layer: prazo urgentes, ja filtrados pelo escopo de acesso."""

from datetime import date, timedelta

from app.models.usuario import Usuario
from app.repositories.prazo_repository import PrazoRepository


class PrazoService:
    def __init__(self, repo: PrazoRepository):
        self.repo = repo

    def listar_urgentes(
        self,
        usuario: Usuario,
        *,
        dias: int = 7,
        pagina: int = 1,
        limite: int = 20,
    ) -> dict:
        ate = date.today() + timedelta(days=dias)
        total, rows = self.repo.listar_urgentes(
            usuario=usuario, ate=ate, pagina=pagina, limite=limite
        )
        itens = [
            {
                "id": prazo.id,
                "caso_id": prazo.caso_id,
                "titulo": prazo.titulo,
                "tipo": prazo.tipo,
                "data_limite": prazo.data_limite,
                "cumprido": prazo.cumprido,
                "numero_processo": numero,
                "cliente": cliente,
            }
            for prazo, numero, cliente in rows
        ]
        return {"itens": itens, "total": total, "pagina": pagina, "limite": limite}
