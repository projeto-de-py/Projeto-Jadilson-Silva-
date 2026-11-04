"""Service Layer: cadastro, atualizacao e listagem de usuarios (RF02).

A conta do advogado principal (campo `administrador`) NUNCA e criada nem
alterada por aqui - ela vem do provisionamento controlado (app/seed.py), o que
impede escalada de privilegios pelo cadastro ou por qualquer endpoint.
"""

from sqlalchemy.exc import IntegrityError

from app.core.security import hash_senha
from app.models.usuario import Perfil, Usuario
from app.repositories.usuario_repository import UsuarioRepository


class EmailJaCadastradoError(Exception):
    pass


class DadosInvalidosError(Exception):
    pass


class UsuarioNaoEncontradoError(Exception):
    pass


_PERFIS = {perfil.value for perfil in Perfil}


class UsuarioService:
    def __init__(self, repo: UsuarioRepository):
        self.repo = repo

    def criar(self, nome: str, email: str, senha: str, perfil: str) -> Usuario:
        email = email.strip().lower()

        if perfil not in _PERFIS:
            raise DadosInvalidosError("Perfil deve ser ADVOGADO ou FUNCIONARIO")
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
            administrador=False,  # privilegio exclusivo do provisionamento
            ativo=True,
        )
        try:
            return self.repo.criar(usuario)
        except IntegrityError:
            # corrida entre o check acima e o INSERT: o banco rejeitou o duplicado
            self.repo.db.rollback()
            raise EmailJaCadastradoError("Ja existe um usuario com este e-mail")

    def atualizar(
        self,
        usuario_id: int,
        *,
        ativo: bool | None = None,
        perfil: str | None = None,
    ) -> Usuario:
        """Ativa/desativa ou troca o perfil funcional (apenas advogado principal).

        `administrador` nem existe nesta API: o campo so muda no banco, pelo
        processo de provisionamento - por isso ninguem escala privilegio aqui.
        """
        usuario = self.repo.buscar_por_id(usuario_id)
        if usuario is None:
            raise UsuarioNaoEncontradoError("Usuario nao encontrado")

        if ativo is not None:
            usuario.ativo = ativo
        if perfil is not None:
            if perfil not in _PERFIS:
                raise DadosInvalidosError("Perfil deve ser ADVOGADO ou FUNCIONARIO")
            usuario.perfil = perfil

        return self.repo.atualizar(usuario)

    def listar(self) -> list[Usuario]:
        return self.repo.listar()
