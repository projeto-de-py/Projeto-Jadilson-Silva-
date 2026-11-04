"""Service Layer: prazos processuais filtrados pelo escopo de acesso."""

from datetime import date, timedelta

from app.models.caso import Caso
from app.models.prazo import Prazo
from app.models.usuario import Usuario
from app.repositories.prazo_repository import PrazoRepository


class PrazoNaoEncontradoError(Exception):
    """Prazo ou caso vinculado inexistente/fora do escopo (404)."""


def _serializar(prazo: Prazo, caso: Caso) -> dict:
    hoje = date.today()
    dias = (prazo.data_limite - hoje).days
    return {
        "id": prazo.id,
        "caso_id": prazo.caso_id,
        "titulo": prazo.titulo,
        "descricao": prazo.descricao,
        "tipo": prazo.tipo,
        "data_limite": prazo.data_limite,
        "cumprido": prazo.cumprido,
        "dias_restantes": dias,
        "numero_processo": caso.numero_processo or f"Caso #{caso.id}",
        "cliente": caso.cliente,
        "area": caso.area,
        "vara": caso.vara or caso.tribunal or "Vara não informada",
    }


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

    def listar_todos(
        self,
        usuario: Usuario,
        *,
        pagina: int = 1,
        limite: int = 100,
    ) -> dict:
        total, rows = self.repo.listar_todos(
            usuario=usuario, pagina=pagina, limite=limite
        )
        itens = [_serializar(prazo, caso) for prazo, caso in rows]
        return {"itens": itens, "total": total, "pagina": pagina, "limite": limite}

    def criar(
        self,
        usuario: Usuario,
        *,
        caso_id: int,
        titulo: str,
        data_limite: date,
        tipo: str = "PROCESSUAL",
        descricao: str | None = None,
    ) -> dict:
        caso = self.repo.buscar_caso_visivel(caso_id, usuario)
        if caso is None:
            raise PrazoNaoEncontradoError("Caso não encontrado")
        prazo = self.repo.criar(
            Prazo(
                caso_id=caso.id,
                titulo=titulo.strip(),
                tipo=(tipo or "PROCESSUAL").strip(),
                data_limite=data_limite,
                descricao=descricao.strip() if descricao else None,
                cumprido=False,
            )
        )
        return _serializar(prazo, caso)

    def alternar_cumprido(
        self,
        usuario: Usuario,
        prazo_id: int,
        *,
        cumprido: bool | None = None,
    ) -> dict:
        achado = self.repo.buscar_visivel(prazo_id, usuario)
        if achado is None:
            raise PrazoNaoEncontradoError("Prazo não encontrado")
        prazo, caso = achado
        prazo.cumprido = (not prazo.cumprido) if cumprido is None else bool(cumprido)
        self.repo.salvar(prazo)
        return _serializar(prazo, caso)

    def excluir(self, usuario: Usuario, prazo_id: int) -> None:
        achado = self.repo.buscar_visivel(prazo_id, usuario)
        if achado is None:
            raise PrazoNaoEncontradoError("Prazo não encontrado")
        prazo, _ = achado
        self.repo.excluir(prazo)
