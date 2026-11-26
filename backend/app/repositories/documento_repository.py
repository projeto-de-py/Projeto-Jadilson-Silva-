"""Padrao Repository: consultas e persistencia de Documento (Fase 3).

Todo SQL mora aqui. Toda listagem aplica o escopo herdado do caso e a
paginacao e feita NO BANCO (offset/limit).
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.documento import Documento
from app.models.usuario import Usuario
from app.repositories.escopo import condicao_documento_visivel


class DocumentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar(
        self,
        *,
        usuario: Usuario,
        q: str | None = None,
        caso_id: int | None = None,
        cliente_id: int | None = None,
        area: str | None = None,
        pagina: int = 1,
        limite: int = 20,
    ) -> tuple[list[Documento], int]:
        """Lista documentos visiveis, com filtros e ordenacao no banco."""
        filtros: list = [condicao_documento_visivel(usuario)]
        if q:
            termo = f"%{q.strip()}%"
            filtros.append(
                Documento.titulo.ilike(termo) | Documento.tipo.ilike(termo)
            )
        if caso_id is not None:
            filtros.append(Documento.caso_id == caso_id)
        if cliente_id is not None:
            filtros.append(Documento.cliente_id == cliente_id)
        if area:
            filtros.append(Documento.area == area)

        total = (
            self.db.scalar(
                select(func.count()).select_from(Documento).where(*filtros)
            )
            or 0
        )
        stmt = (
            select(Documento)
            .where(*filtros)
            .order_by(Documento.atualizado_em.desc(), Documento.id.desc())
            .offset((pagina - 1) * limite)
            .limit(limite)
        )
        return list(self.db.scalars(stmt)), int(total)

    def buscar_visivel(
        self, documento_id: int, usuario: Usuario
    ) -> Documento | None:
        """Documento apenas quando o usuario ve o caso dele (senao None -> 404)."""
        return self.db.scalar(
            select(Documento).where(
                Documento.id == documento_id,
                condicao_documento_visivel(usuario),
            )
        )

    def criar(self, documento: Documento) -> Documento:
        self.db.add(documento)
        self.db.commit()
        self.db.refresh(documento)
        return documento

    def atualizar(self, documento: Documento) -> Documento:
        self.db.add(documento)
        self.db.commit()
        self.db.refresh(documento)
        return documento

    def excluir(self, documento: Documento) -> None:
        self.db.delete(documento)
        self.db.commit()
