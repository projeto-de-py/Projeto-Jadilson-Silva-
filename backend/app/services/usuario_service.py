"""Service Layer: cadastro e listagem de usuarios (apenas Admin - RF02)."""

from sqlalchemy.exc import IntegrityError

from app.core.security import hash_senha
from app.models.usuario import Perfil, Usuario
from app.repositories.usuario_repository import UsuarioRepository


class EmailJaCadastradoError(Exception):
    pass


class DadosInvalidosError(Exception):
    pass


class UsuarioService:
    def __init__(self, repo: UsuarioRepository):
        self.repo = repo

    def criar(self, nome: str, email: str, senha: str, perfil: str) -> Usuario:
        email = email.strip().lower()

        if perfil not in {p.value for p in Perfil}:
            raise DadosInvalidosError("Perfil deve ser ADMIN ou PADRAO")
        if len(senha) < 6:
            raise DadosInvalidosError("A senha deve ter pelo menos 6 caracteres")
        if self.repo.buscar_por_email(email) is not None:
            raise EmailJaCadastradoError("Ja existe um usuario com este e-mail")

        try:
            senha_hash = hash_senha(senha)
        except ValueError:
            # bcrypt aceita no maximo 72 bytes (ex.: senhas com emojis/acentos
            # passam do limite mesmo com menos de 72 caracteres)
            raise DadosInvalidosError("A senha e longa demais (maximo 72 bytes)")

        usuario = Usuario(
            nome=nome.strip(),
            email=email,
            senha_hash=senha_hash,
            perfil=perfil,
            ativo=True,
        )
        try:
            return self.repo.criar(usuario)
        except IntegrityError:
            # corrida entre o check acima e o INSERT: o banco rejeitou o duplicado
            self.repo.db.rollback()
            raise EmailJaCadastradoError("Ja existe um usuario com este e-mail")

    def listar(self) -> list[Usuario]:
        return self.repo.listar()
