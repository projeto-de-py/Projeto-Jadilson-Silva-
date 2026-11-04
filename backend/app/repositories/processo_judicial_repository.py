"""Padrao Repository: consultas e persistencia de ProcessoJudicial (Fase 3).

Todo SQL mora aqui. Toda listagem aplica o escopo de acesso (herdado do caso)
e a paginacao e feita NO BANCO (offset/limit).
"""

from datetime import date

from sqlalchemy import false, func, select
from sqlalchemy.orm import Session

from app.models.processo_judicial import ProcessoJudicial
from app.models.usuario import Usuario
from app.core.validacao import digitos
from app.repositories.escopo import condicao_processo_visivel


class ProcessoJudicialRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar(
        self,
        *,
        usuario: Usuario,
        q: str | None = None,
        caso_id: int | None = None,
        tribunal: str | None = None,
        comarca: str | None = None,
        instancia: str | None = None,
        classe_processual: str | None = None,
        status: str | None = None,
        distribuicao_de: date | None = None,
        distribuicao_ate: date | None = None,
        arquivado: bool = False,
        pagina: int = 1,
        limite: int = 20,
    ) -> tuple[list[ProcessoJudicial], int]:
        """Lista processos paginados com escopo, filtros e ordenacao no banco.

        `q` busca pelo numero CNJ (normaliza para digitos, aceita parcial).
        `arquivado=False` (padrao) esconde os processos arquivados.
        """
        filtros: list = [
            condicao_processo_visivel(usuario),
            ProcessoJudicial.arquivado.is_(bool(arquivado)),
        ]
        if q:
            # `q` e busca pelo NUMERO: normaliza para digitos. Um termo sem
            # nenhum digito nao pode casar com todos os numeros ("%%"), entao
            # ele casa com nenhum.
            termo = digitos(q)
            if not termo:
                filtros.append(false())
            else:
                filtros.append(ProcessoJudicial.numero_processo.ilike(f"%{termo}%"))
        if caso_id is not None:
            filtros.append(ProcessoJudicial.caso_id == caso_id)
        if tribunal:
            filtros.append(ProcessoJudicial.tribunal.ilike(f"%{tribunal.strip()}%"))
        if comarca:
            filtros.append(ProcessoJudicial.comarca.ilike(f"%{comarca.strip()}%"))
        if instancia:
            filtros.append(ProcessoJudicial.instancia == instancia)
        if classe_processual:
            filtros.append(
                ProcessoJudicial.classe_processual.ilike(f"%{classe_processual.strip()}%")
            )
        if status:
            filtros.append(ProcessoJudicial.status == status)
        if distribuicao_de is not None:
            filtros.append(ProcessoJudicial.data_distribuicao >= distribuicao_de)
        if distribuicao_ate is not None:
            filtros.append(ProcessoJudicial.data_distribuicao <= distribuicao_ate)

        total = (
            self.db.scalar(
                select(func.count()).select_from(ProcessoJudicial).where(*filtros)
            )
            or 0
        )

        stmt = (
            select(ProcessoJudicial)
            .where(*filtros)
            .order_by(
                ProcessoJudicial.data_distribuicao.desc(),
                ProcessoJudicial.criado_em.desc(),
                ProcessoJudicial.id.desc(),
            )
            .offset((pagina - 1) * limite)
            .limit(limite)
        )
        return list(self.db.scalars(stmt)), int(total)

    def listar_por_caso(
        self, caso_id: int, usuario: Usuario, *, arquivado: bool = False
    ) -> list[ProcessoJudicial]:
        """Processos de um caso, aplicando o escopo (404 se caso inacessivel)."""
        filtros = [
            condicao_processo_visivel(usuario),
            ProcessoJudicial.caso_id == caso_id,
            ProcessoJudicial.arquivado.is_(bool(arquivado)),
        ]
        stmt = (
            select(ProcessoJudicial)
            .where(*filtros)
            .order_by(
                ProcessoJudicial.data_distribuicao.desc(),
                ProcessoJudicial.id.desc(),
            )
        )
        return list(self.db.scalars(stmt))

    def buscar_visivel(
        self, processo_id: int, usuario: Usuario, *, incluir_arquivados: bool = True
    ) -> ProcessoJudicial | None:
        """Processo apenas quando o usuario ve o caso dele (senao None -> 404).

        Um processo nunca expoe um caso fora do escopo: o filtro de escopo do
        caso e aplicado aqui.
        """
        filtros = [
            ProcessoJudicial.id == processo_id,
            condicao_processo_visivel(usuario),
        ]
        if not incluir_arquivados:
            filtros.append(ProcessoJudicial.arquivado.is_(False))
        return self.db.scalar(select(ProcessoJudicial).where(*filtros))

    def existe_numero(self, numero_normalizado: str) -> bool:
        """Checa unicidade do numero CNJ (normalizado) no banco."""
        return (
            self.db.scalar(
                select(func.count())
                .select_from(ProcessoJudicial)
                .where(ProcessoJudicial.numero_processo == numero_normalizado)
            )
            or 0
        ) > 0

    def criar(self, processo: ProcessoJudicial) -> ProcessoJudicial:
        self.db.add(processo)
        self.db.commit()
        self.db.refresh(processo)
        return processo

    def atualizar(self, processo: ProcessoJudicial) -> ProcessoJudicial:
        """Commit da atualizacao/arquivamento (objeto ja na sessao)."""
        self.db.add(processo)
        self.db.commit()
        self.db.refresh(processo)
        return processo
