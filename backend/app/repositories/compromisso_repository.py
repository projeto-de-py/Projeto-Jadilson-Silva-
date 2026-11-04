"""Padrao Repository: consultas de Compromisso (Fase 4).

Todo SQL mora aqui. Toda listagem aplica o escopo de acesso (casos da Fase 1;
compromissos sem caso, somente o administrador) e a paginacao e feita NO
BANCO (offset/limit). A agenda e filtrada por HORARIO LOCAL do escritorio.
"""

from datetime import date, datetime, time

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.compromisso import Compromisso
from app.models.usuario import Usuario
from app.repositories.escopo import condicao_compromisso_visivel


def _inicio_do_dia(dia: date) -> datetime:
    return datetime.combine(dia, time.min)


def _fim_do_dia(dia: date) -> datetime:
    # Horario local do escritorio: o ultimo instante do dia pedido.
    return datetime.combine(dia, time.max)


class CompromissoRepository:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------- escrita
    # SEM commit aqui de proposito: o negocio e a auditoria
    # (compromisso_historicos) dividem a MESMA transacao, fechada pelo
    # CompromissoService (commit unico ou rollback total).

    def criar(self, compromisso: Compromisso) -> Compromisso:
        self.db.add(compromisso)
        self.db.flush()  # atribui id/criado_em sem fechar a transacao
        return compromisso

    def atualizar(self, compromisso: Compromisso) -> Compromisso:
        """Garante a escrita na transacao atual (commit fica no service)."""
        self.db.flush()
        return compromisso

    def confirmar(self) -> None:
        """Fecha a transacao (negocio + auditoria) em um unico commit."""
        self.db.commit()

    def desfazer(self) -> None:
        """Reverte TUDO: alteracao do compromisso e registros de historico."""
        self.db.rollback()

    # ------------------------------------------------------------- leitura

    def buscar_visivel(self, compromisso_id: int, usuario: Usuario) -> Compromisso | None:
        """Compromisso pelo id, restrito ao escopo do usuario (None = 404)."""
        stmt = select(Compromisso).where(
            Compromisso.id == compromisso_id,
            condicao_compromisso_visivel(usuario),
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
        inicio_de: date | None = None,
        inicio_ate: date | None = None,
        pagina: int = 1,
        limite: int = 20,
    ) -> tuple[int, list[Compromisso]]:
        """Lista paginada sob escopo do usuario (filtros aplicados no banco)."""
        filtros = [condicao_compromisso_visivel(usuario)]

        if q:
            like = f"%{q}%"
            filtros.append(
                or_(Compromisso.titulo.ilike(like), Compromisso.descricao.ilike(like))
            )
        if caso_id is not None:
            filtros.append(Compromisso.caso_id == caso_id)
        if processo_id is not None:
            filtros.append(Compromisso.processo_id == processo_id)
        if responsavel_id is not None:
            filtros.append(Compromisso.responsavel_id == responsavel_id)
        if tipo is not None:
            filtros.append(Compromisso.tipo == tipo)
        if status is not None:
            filtros.append(Compromisso.status == status)
        if inicio_de is not None:
            filtros.append(Compromisso.data_inicio >= _inicio_do_dia(inicio_de))
        if inicio_ate is not None:
            filtros.append(Compromisso.data_inicio <= _fim_do_dia(inicio_ate))

        total = (
            self.db.scalar(
                select(func.count()).select_from(Compromisso).where(*filtros)
            )
            or 0
        )
        stmt = (
            select(Compromisso)
            .where(*filtros)
            .order_by(Compromisso.data_inicio.asc(), Compromisso.id.asc())
            .offset((pagina - 1) * limite)
            .limit(limite)
        )
        return int(total), list(self.db.scalars(stmt))

    def listar_agenda(
        self,
        *,
        usuario: Usuario,
        de: date,
        ate: date,
        responsavel_id: int | None = None,
        pagina: int = 1,
        limite: int = 50,
    ) -> tuple[int, list[Compromisso]]:
        """Compromissos do periodo, em ordem de horario (sem misturar prazos).

        A agenda e um recorte temporal dos compromissos: herda o escopo de
        acesso e nunca expoe compromissos de casos nao autorizados.

        SEMANTICA DE SOBREPOSICAO: entra tudo que OVERLAP o periodo - inclusive
        o compromisso que comeca ANTES de `de` e termina dentro dele (eventos
        que atravessam a virada do periodo). A ordenacao e por `data_inicio`.
        """
        filtros = [
            condicao_compromisso_visivel(usuario),
            # termina (ou esta em curso) a partir do inicio do dia `de`
            Compromisso.data_fim >= _inicio_do_dia(de),
            # comeca ate o fim do dia `ate`
            Compromisso.data_inicio <= _fim_do_dia(ate),
        ]
        if responsavel_id is not None:
            filtros.append(Compromisso.responsavel_id == responsavel_id)

        total = (
            self.db.scalar(
                select(func.count()).select_from(Compromisso).where(*filtros)
            )
            or 0
        )
        stmt = (
            select(Compromisso)
            .where(*filtros)
            .order_by(Compromisso.data_inicio.asc(), Compromisso.id.asc())
            .offset((pagina - 1) * limite)
            .limit(limite)
        )
        return int(total), list(self.db.scalars(stmt))
