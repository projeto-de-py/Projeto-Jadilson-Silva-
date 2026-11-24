"""Padrao Repository: consultas de Andamento (Fase 6/RF06).

Todo SQL mora aqui. Toda listagem aplica o escopo de acesso do caso (Fase 1) e
a paginacao e feita NO BANCO (offset/limit). O ordenador cronologico e
`ocorrido_em` (data/hora da movimentacao) com desempate por `id`, permitindo
ordem crescente (linha do tempo ascendente) ou decrescente (feed da UI).

O nome do responsavel (`criado_por_nome`) vem de um LEFT JOIN com `usuarios`:
o usuario pode ser excluido do sistema (`ondelete=SET NULL`) e o registro
historico permanece, apenas sem o nome.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.andamento import Andamento
from app.models.usuario import Usuario
from app.repositories.escopo import condicao_andamento_visivel

_ORDEM = {"asc": (Andamento.ocorrido_em.asc(), Andamento.id.asc()),
          "desc": (Andamento.ocorrido_em.desc(), Andamento.id.desc())}


class AndamentoRepository:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------- leitura

    def buscar_visivel(
        self, andamento_id: int, usuario: Usuario
    ) -> tuple[Andamento, str | None] | None:
        """Andamento pelo id (do caso informado), restrito ao escopo (None = 404)."""
        stmt = (
            select(Andamento, Usuario.nome)
            .outerjoin(Usuario, Andamento.criado_por_id == Usuario.id)
            .where(
                Andamento.id == andamento_id,
                condicao_andamento_visivel(usuario),
            )
        )
        row = self.db.execute(stmt).first()
        if row is None:
            return None
        return row[0], row[1]

    def listar(
        self,
        *,
        caso_id: int,
        usuario: Usuario,
        pagina: int = 1,
        limite: int = 20,
        ordem: str = "desc",
    ) -> tuple[int, list[tuple[Andamento, str | None]]]:
        """Andamentos de um caso sob escopo do usuario (paginado no banco)."""
        filtros = [
            Andamento.caso_id == caso_id,
            condicao_andamento_visivel(usuario),
        ]
        total = (
            self.db.scalar(
                select(func.count()).select_from(Andamento).where(*filtros)
            )
            or 0
        )
        stmt = (
            select(Andamento, Usuario.nome)
            .outerjoin(Usuario, Andamento.criado_por_id == Usuario.id)
            .where(*filtros)
            .order_by(*_ORDEM[ordem])
            .offset((pagina - 1) * limite)
            .limit(limite)
        )
        rows = self.db.execute(stmt).all()
        return int(total), [(item, nome) for item, nome in rows]

    # ------------------------------------------------------------- escrita
    # SEM commit aqui de proposito: o registro e a sua identidade (id/criado)
    # nascem na MESMA transacao controlada pelo AndamentoService.

    def criar(self, andamento: Andamento) -> Andamento:
        self.db.add(andamento)
        self.db.flush()  # atribui id sem fechar a transacao
        return andamento

    def confirmar(self) -> None:
        """Fecha a transacao do registro em um unico commit."""
        self.db.commit()

    def desfazer(self) -> None:
        """Reverte o registro (nada fica gravado parcialmente)."""
        self.db.rollback()
