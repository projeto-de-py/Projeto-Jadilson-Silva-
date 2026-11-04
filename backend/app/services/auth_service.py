"""Service Layer: regras de negocio de autenticacao (RF01 e RF02)."""

import secrets

from app.core import security
from app.models.usuario import Usuario
from app.repositories.usuario_repository import UsuarioRepository

# Hash bcrypt valido, usado apenas para equalizar o tempo de resposta do login
# quando o e-mail nao existe (evita enumeracao por timing - ver autenticar()).
_HASH_DUMMY = security.hash_senha("timing-equalizador-nao-e-uma-senha")


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

        if usuario is None:
            security.verificar_senha(senha, _HASH_DUMMY)
            raise ErroAutenticacao("E-mail ou senha invalidos")

        if not security.verificar_senha(senha, usuario.senha_hash):
            raise ErroAutenticacao("E-mail ou senha invalidos")

        if not usuario.ativo:
            raise UsuarioInativoError("Usuario inativo. Contate o administrador.")

        return usuario

    def gerar_sessao(self, usuario: Usuario) -> tuple[str, str]:
        """Gera o JWT (com claim `csrf` embutido) e o token CSRF para o front.

        Retorna (token_para_cookie, csrf_para_o_corpo_da_resposta).
        """
        csrf = secrets.token_urlsafe(32)
        token = security.criar_token(
            subject=str(usuario.id), perfil=usuario.perfil, csrf=csrf
        )
        return token, csrf

    def alterar_senha(
        self, usuario: Usuario, senha_atual: str, nova_senha: str
    ) -> Usuario:
        """Valida a senha atual e persiste o novo hash bcrypt no banco."""
        if not security.verificar_senha(senha_atual, usuario.senha_hash):
            raise ErroAutenticacao("A senha atual informada está incorreta.")
        usuario.senha_hash = security.hash_senha(nova_senha)
        return self.repo.atualizar(usuario)
