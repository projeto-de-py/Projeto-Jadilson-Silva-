"""Padrao Repository: consultas e persistencia de Caso (todo SQL mora aqui).

Toda listagem aplica o escopo de acesso da Fase 1 e a paginacao e feita NO
BANCO (offset/limit) - nunca carregamos tudo para filtrar em memoria.
"""

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models.caso import Caso, ORDEM_PRIORIDADE
from app.models.usuario import Usuario
from app.repositories.escopo import condicao_caso_visivel


class CasoRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar(
        self,
        *,
        usuario: Usuario,
        q: str | None = None,
        cliente_id: int | None = None,
        area: str | None = None,
        status: str | None = None,
        prioridade: str | None = None,
        responsavel_id: int | None = None,
        tipo_demanda: str | None = None,
        arquivado: bool = False,
        ordenar: str = "abertura",
        pagina: int = 1,
        limite: int = 20,
    ) -> tuple[list[Caso], int]:
        """Lista casos paginados com escopo, filtros e ordenacao no banco.

        `arquivado=False` (padrao) esconde os casos arquivados das listagens
        normais; a listagem de arquivados usa `arquivado=True`.
        """
        filtros: list = [
            condicao_caso_visivel(usuario),
            Caso.arquivado.is_(bool(arquivado)),
        ]
        if q:
            termo = f"%{q.strip()}%"
            filtros.append(
                or_(
                    Caso.titulo.ilike(termo),
                    Caso.numero_processo.ilike(termo),
                    Caso.cliente.ilike(termo),
                    Caso.parte_contraria.ilike(termo),
                )
            )
        if cliente_id is not None:
            filtros.append(Caso.cliente_id == cliente_id)
        if area:
            filtros.append(Caso.area == area)
        if status:
            filtros.append(Caso.status == status)
        if prioridade:
            filtros.append(Caso.prioridade == prioridade)
        if responsavel_id is not None:
            filtros.append(Caso.responsavel_id == responsavel_id)
        if tipo_demanda:
            filtros.append(Caso.tipo_demanda == tipo_demanda)

        total = self.db.scalar(select(func.count()).select_from(Caso).where(*filtros)) or 0

        if ordenar == "prioridade":
            # URGENTE primeiro: a ordem alfabetica nao reflete a prioridade.
            peso = case(
                *[(Caso.prioridade == nome, valor) for nome, valor in ORDEM_PRIORIDADE.items()],
                else_=0,
            )
            ordem = (peso.desc(), Caso.data_abertura.desc(), Caso.id.desc())
        else:  # "abertura" (padrao): mais recentes primeiro
            ordem = (Caso.data_abertura.desc(), Caso.criado_em.desc(), Caso.id.desc())

        stmt = (
            select(Caso)
            .where(*filtros)
            .order_by(*ordem)
            .offset((pagina - 1) * limite)
            .limit(limite)
        )
        return list(self.db.scalars(stmt)), int(total)

    def buscar_visivel(
        self, caso_id: int, usuario: Usuario, *, incluir_arquivados: bool = True
    ) -> Caso | None:
        """Devolve o caso apenas quando o usuario tem acesso a ele.

        Caso inexistente e caso sem permissao devolvem o mesmo `None`: a rota
        responde 404 e nao expoe a existencia de casos de outros advogados.
        Casos arquivados continuam acessiveis pela rota de detalhe (mantem o
        historico consultavel), mas ficam fora das listagens padrao.
        """
        filtros = [Caso.id == caso_id, condicao_caso_visivel(usuario)]
        if not incluir_arquivados:
            filtros.append(Caso.arquivado.is_(False))
        return self.db.scalar(select(Caso).where(*filtros))

    def criar(self, caso: Caso) -> Caso:
        self.db.add(caso)
        self.db.commit()
        self.db.refresh(caso)
        return caso

    def atualizar(self, caso: Caso) -> Caso:
        """Commit da atualizacao/arquivamento (objeto ja na sessao)."""
        self.db.add(caso)
        self.db.commit()
        self.db.refresh(caso)
        return caso
