"""Padrao Repository: consultas de Prazo (com o escopo de acesso do usuario).

Todo SQL mora aqui. Toda listagem aplica o escopo da Fase 1 e a paginacao e
feita NO BANCO (offset/limit). O "vencido" e calculado no banco a partir da
data local de Brasilia (parametro `hoje`) - nunca e armazenado.
"""

from datetime import date

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.core.tempo import hoje_brasilia
from app.models.caso import Caso, ORDEM_PRIORIDADE
from app.models.prazo import Prazo, StatusPrazo
from app.models.usuario import Usuario
from app.repositories.escopo import condicao_prazo_visivel

_ABERTOS = (StatusPrazo.PENDENTE.value, StatusPrazo.EM_ANDAMENTO.value)

# Grau da prioridade em SQL (URGENTE = 4 primeiro) para ordenar no banco.
_CASE_PRIORIDADE = case(
    *[(Prazo.prioridade == valor, grau) for valor, grau in ORDEM_PRIORIDADE.items()],
    else_=0,
)


class PrazoRepository:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------- leitura

    def buscar_visivel(self, prazo_id: int, usuario: Usuario) -> Prazo | None:
        """Prazo pelo id, restrito ao escopo do usuario (None = 404)."""
        stmt = select(Prazo).where(
            Prazo.id == prazo_id, condicao_prazo_visivel(usuario)
        )
        return self.db.scalar(stmt)

    def listar(
        self,
        *,
        usuario: Usuario,
        q: str | None = None,
        caso_id: int | None = None,
        processo_id: int | None = None,
        responsavel_id: int | None = None,
        tipo: str | None = None,
        status: str | None = None,
        prioridade: str | None = None,
        vencimento_de: date | None = None,
        vencimento_ate: date | None = None,
        vencidos: bool | None = None,
        pendentes: bool | None = None,
        concluidos: bool | None = None,
        pagina: int = 1,
        limite: int = 20,
    ) -> tuple[int, list[Prazo]]:
        """Lista paginada sob escopo do usuario (filtros aplicados no banco)."""
        hoje = hoje_brasilia()
        filtros = [condicao_prazo_visivel(usuario)]

        if q:
            like = f"%{q}%"
            filtros.append(or_(Prazo.titulo.ilike(like), Prazo.descricao.ilike(like)))
        if caso_id is not None:
            filtros.append(Prazo.caso_id == caso_id)
        if processo_id is not None:
            filtros.append(Prazo.processo_id == processo_id)
        if responsavel_id is not None:
            filtros.append(Prazo.responsavel_id == responsavel_id)
        if tipo is not None:
            filtros.append(Prazo.tipo == tipo)
        if status is not None:
            filtros.append(Prazo.status == status)
        if prioridade is not None:
            filtros.append(Prazo.prioridade == prioridade)
        if vencimento_de is not None:
            filtros.append(Prazo.data_vencimento >= vencimento_de)
        if vencimento_ate is not None:
            filtros.append(Prazo.data_vencimento <= vencimento_ate)
        if vencidos is not None:
            cond = self._condicao_vencido(hoje)
            filtros.append(cond if vencidos else ~cond)
        if pendentes is not None:
            # SEMANTICA EXPLICITA: "pendentes" = PRAZOS EM ABERTO, ou seja
            # PENDENTE ou EM_ANDAMENTO (CONCLUIDO/CANCELADO ficam de fora).
            cond = Prazo.status.in_(_ABERTOS)
            filtros.append(cond if pendentes else ~cond)
        if concluidos is not None:
            cond = Prazo.status == StatusPrazo.CONCLUIDO.value
            filtros.append(cond if concluidos else ~cond)

        total = (
            self.db.scalar(select(func.count()).select_from(Prazo).where(*filtros)) or 0
        )
        stmt = (
            select(Prazo)
            .where(*filtros)
            .order_by(
                Prazo.data_vencimento.asc(),
                _CASE_PRIORIDADE.desc(),
                Prazo.id.asc(),
            )
            .offset((pagina - 1) * limite)
            .limit(limite)
        )
        return int(total), list(self.db.scalars(stmt))

    def listar_urgentes(
        self,
        *,
        usuario: Usuario,
        ate: date,
        hoje: date,
        pagina: int = 1,
        limite: int = 20,
    ) -> tuple[int, list[tuple[Prazo, str | None, str | None]]]:
        """Prazos abertos (pendentes/em andamento) vencidos ou ate `ate`.

        Ordena por situacao (VENCIDO, HOJE, PROXIMO), depois pela prioridade
        cadastrada e por fim pela data - sempre restrito ao escopo do usuario.
        """
        filtros = [
            Prazo.status.in_(_ABERTOS),
            Prazo.data_vencimento <= ate,
            condicao_prazo_visivel(usuario),
        ]
        total = (
            self.db.scalar(select(func.count()).select_from(Prazo).where(*filtros)) or 0
        )
        situacao = case(
            (Prazo.data_vencimento < hoje, 0),
            (Prazo.data_vencimento == hoje, 1),
            else_=2,
        )
        stmt = (
            select(Prazo, Caso.numero_processo, Caso.cliente)
            .join(Caso)
            .where(*filtros)
            .order_by(situacao.asc(), _CASE_PRIORIDADE.desc(),
                      Prazo.data_vencimento.asc(), Prazo.id.asc())
            .offset((pagina - 1) * limite)
            .limit(limite)
        )
        rows = self.db.execute(stmt).all()
        return int(total), [(prazo, numero, cliente) for prazo, numero, cliente in rows]

    # ------------------------------------------------------------- escrita
    # SEM commit aqui de proposito: o negocio e a auditoria
    # (prazo_historicos) precisam dividir a MESMA transacao. O PrazoService
    # e quem faz flush + commit unico (ou rollback total em caso de falha).

    def criar(self, prazo: Prazo) -> Prazo:
        self.db.add(prazo)
        self.db.flush()  # atribui id/criado_em sem fechar a transacao
        return prazo

    def atualizar(self, prazo: Prazo) -> Prazo:
        """Garante a escrita na transacao atual (commit fica no service)."""
        self.db.flush()
        return prazo

    def confirmar(self) -> None:
        """Fecha a transacao (negocio + auditoria) em um unico commit."""
        self.db.commit()

    def desfazer(self) -> None:
        """Reverte TUDO: alteracao do prazo e registros de historico."""
        self.db.rollback()

    # ------------------------------------------------------------- privado

    @staticmethod
    def _condicao_vencido(hoje: date):
        """Vencido = em aberto com data de vencimento anterior a `hoje`."""
        return and_(
            Prazo.status.in_(_ABERTOS),
            Prazo.data_vencimento < hoje,
        )
