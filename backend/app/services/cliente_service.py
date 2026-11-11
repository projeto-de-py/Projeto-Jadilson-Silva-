"""Service Layer: regras de negocio de clientes (cadastro, consulta, atualizacao e remocao)."""

from datetime import date

from sqlalchemy.exc import IntegrityError

from app.core.validacao import (
    DocumentoInvalidoError,
    TelefoneInvalidoError,
    normalizar_documento,
    normalizar_telefone,
)
from app.models.cliente import Cliente
from app.models.usuario import Usuario
from app.repositories.cliente_repository import ClienteRepository


class ClienteNaoEncontradoError(Exception):
    """Cliente inexistente OU fora do escopo de acesso do usuario (404)."""


class DocumentoJaCadastradoError(Exception):
    """CPF/CNPJ ja cadastrado em outro cliente (409)."""


class DadosInvalidosError(Exception):
    """Dado cadastral fora das regras aceitas (422)."""


class ClienteService:
    def __init__(self, repo: ClienteRepository):
        self.repo = repo

    def criar(
        self,
        *,
        nome: str,
        cpf_cnpj: str | None = None,
        email: str | None = None,
        telefone: str | None = None,
        data_nascimento: date | None = None,
    ) -> Cliente:
        documento = normalizar_documento(cpf_cnpj)
        fone = normalizar_telefone(telefone)
        email_norm = email.strip().lower() if email else None
        nome_norm = nome.strip()

        if data_nascimento is not None and data_nascimento > date.today():
            raise DadosInvalidosError(
                "Data de nascimento nao pode ser no futuro"
            )

        if documento is not None and self.repo.buscar_por_documento(documento):
            raise DocumentoJaCadastradoError(
                "Ja existe um cliente com este CPF/CNPJ"
            )

        cliente = Cliente(
            nome=nome_norm,
            cpf_cnpj=documento,
            email=email_norm,
            telefone=fone,
            data_nascimento=data_nascimento,
            ativo=True,
        )
        try:
            return self.repo.criar(cliente)
        except IntegrityError:
            self.repo.db.rollback()
            raise DocumentoJaCadastradoError(
                "Ja existe um cliente com este CPF/CNPJ"
            )

    def atualizar(
        self,
        cliente_id: int,
        *,
        nome: str | None = None,
        cpf_cnpj: str | None = None,
        email: str | None = None,
        telefone: str | None = None,
        data_nascimento: date | None = None,
        ativo: bool | None = None,
    ) -> Cliente:
        cliente = self.repo.buscar_por_id(cliente_id)
        if cliente is None:
            raise ClienteNaoEncontradoError("Cliente nao encontrado")

        if nome is not None:
            nome_norm = nome.strip()
            if not nome_norm:
                raise DadosInvalidosError("Nome e obrigatorio")
            cliente.nome = nome_norm

        if cpf_cnpj is not None:
            documento = normalizar_documento(cpf_cnpj)
            if documento is not None:
                existente = self.repo.buscar_por_documento(documento)
                if existente and existente.id != cliente.id:
                    raise DocumentoJaCadastradoError(
                        "Ja existe um cliente com este CPF/CNPJ"
                    )
            cliente.cpf_cnpj = documento

        if email is not None:
            cliente.email = email.strip().lower() if email.strip() else None

        if telefone is not None:
            cliente.telefone = normalizar_telefone(telefone)

        if data_nascimento is not None:
            if data_nascimento > date.today():
                raise DadosInvalidosError(
                    "Data de nascimento nao pode ser no futuro"
                )
            cliente.data_nascimento = data_nascimento

        if ativo is not None:
            cliente.ativo = ativo

        try:
            return self.repo.salvar(cliente)
        except IntegrityError:
            self.repo.db.rollback()
            raise DocumentoJaCadastradoError(
                "Ja existe um cliente com este CPF/CNPJ"
            )

    def listar(
        self,
        usuario: Usuario,
        *,
        q: str | None = None,
        pagina: int = 1,
        limite: int = 20,
    ) -> dict:
        itens, total = self.repo.listar(
            usuario=usuario, q=q, pagina=pagina, limite=limite
        )
        return {
            "itens": itens,
            "total": total,
            "pagina": pagina,
            "limite": limite,
        }

    def buscar(self, cliente_id: int, usuario: Usuario) -> Cliente:
        cliente = self.repo.buscar_visivel(cliente_id, usuario)
        if cliente is None:
            raise ClienteNaoEncontradoError("Cliente nao encontrado")
        return cliente

    def remover(self, cliente_id: int, usuario: Usuario) -> None:
        cliente = self.repo.buscar_visivel(cliente_id, usuario)
        if cliente is None:
            raise ClienteNaoEncontradoError("Cliente nao encontrado")
        self.repo.remover(cliente)


__all__ = [
    "ClienteService",
    "ClienteNaoEncontradoError",
    "DocumentoJaCadastradoError",
    "DadosInvalidosError",
    "DocumentoInvalidoError",
    "TelefoneInvalidoError",
]
