"""Padrao Repository: consultas e persistencia de Cliente."""

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from app.models.assinatura import Assinatura
from app.models.caso import Caso
from app.models.cliente import Cliente
from app.models.cobranca import Cobranca
from app.models.usuario import Usuario
from app.repositories.escopo import condicao_cliente_visivel


class ClienteRepository:
    def __init__(self, db: Session):
        self.db = db

    def buscar_por_documento(self, cpf_cnpj: str) -> Cliente | None:
        """Busca pelo documento ja normalizado (somente digitos)."""
        stmt = select(Cliente).where(Cliente.cpf_cnpj == cpf_cnpj)
        return self.db.scalar(stmt)

    def buscar_por_id(self, cliente_id: int) -> Cliente | None:
        """Cliente pelo id, SEM escopo - uso exclusivo do service quando o
        proprio operador ja e administrador ou quando a regra de acesso e
        conferida em seguida (validar_acesso)."""
        return self.db.get(Cliente, cliente_id)

    def buscar_visivel(self, cliente_id: int, usuario: Usuario) -> Cliente | None:
        """Cliente apenas se pertencer a um caso acessivel ao usuario."""
        stmt = select(Cliente).where(
            Cliente.id == cliente_id, condicao_cliente_visivel(usuario)
        )
        return self.db.scalar(stmt)

    def listar(
        self,
        *,
        usuario: Usuario,
        q: str | None = None,
        pagina: int = 1,
        limite: int = 20,
    ) -> tuple[list[Cliente], int]:
        """Lista clientes paginados respeitando o escopo do usuario."""
        filtros: list = [condicao_cliente_visivel(usuario)]
        if q:
            condicoes_busca = [Cliente.nome.ilike(f"%{q.strip()}%")]
            apenas_digitos = "".join(c for c in q if c.isdigit())
            if apenas_digitos:
                condicoes_busca.append(
                    Cliente.cpf_cnpj.like(f"%{apenas_digitos}%")
                )
            filtros.append(or_(*condicoes_busca))

        total = (
            self.db.scalar(
                select(func.count()).select_from(Cliente).where(*filtros)
            )
            or 0
        )
        stmt = (
            select(Cliente)
            .where(*filtros)
            .order_by(Cliente.nome, Cliente.id)
            .offset((pagina - 1) * limite)
            .limit(limite)
        )
        return list(self.db.scalars(stmt)), int(total)

    def criar(self, cliente: Cliente) -> Cliente:
        self.db.add(cliente)
        self.db.commit()
        self.db.refresh(cliente)
        return cliente

    def salvar(self, cliente: Cliente) -> Cliente:
        self.db.add(cliente)
        self.db.commit()
        self.db.refresh(cliente)
        return cliente

    def remover(self, cliente: Cliente) -> None:
        self.db.execute(
            update(Caso)
            .where(Caso.cliente_id == cliente.id)
            .values(cliente_id=None)
        )
        self.db.execute(
            update(Assinatura)
            .where(Assinatura.cliente_id == cliente.id)
            .values(cliente_id=None)
        )
        self.db.execute(
            delete(Cobranca).where(Cobranca.cliente_id == cliente.id)
        )
        self.db.delete(cliente)
        self.db.commit()
