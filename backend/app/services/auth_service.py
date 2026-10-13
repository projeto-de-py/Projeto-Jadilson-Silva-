"""Service Layer: regras de negocio de autenticacao (RF01 e RF02)."""

from app.core import security
from app.models.usuario import Usuario
from app.repositories.usuario_repository import UsuarioRepository


class ErroAutenticacao(Exception):
    """Credenciais invalidas - mensagem generica para nao vazar se o email existe."""


class UsuarioInativoError(Exception):
    """Usuario cadastrado mas desativado pelo Admin."""


class AuthService:
    def __init__(self, repo: UsuarioRepository):
        self.repo = repo

    def autenticar(self, email: str, senha: str) -> Usuario:
        """RF01: valida email/senha. Lanca ErroAutenticacao ou UsuarioInativoError."""
        email = email.strip().lower()
        usuario = self.repo.buscar_por_email(email)

        if usuario is None or not security.verificar_senha(senha, usuario.senha_hash):
            raise ErroAutenticacao("E-mail ou senha invalidos")

        if not usuario.ativo:
            raise UsuarioInativoError("Usuario inativo. Contate o administrador.")

        return usuario

    def gerar_token(self, usuario: Usuario) -> str:
        return security.criar_token(subject=str(usuario.id), perfil=usuario.perfil)
