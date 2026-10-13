"""Service Layer: cadastro e listagem de usuarios (apenas Admin - RF02)."""

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

        usuario = Usuario(
            nome=nome.strip(),
            email=email,
            senha_hash=hash_senha(senha),
            perfil=perfil,
            ativo=True,
        )
        return self.repo.criar(usuario)

    def listar(self) -> list[Usuario]:
        return self.repo.listar()
