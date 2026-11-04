"""Service Layer: concessao e revogacao de acesso a caso (Fase 1).

O gate administrativo (somente o advogado principal) e aplicado UNICAMENTE na
rota, via dependencia `require_admin` - aqui ficam as regras de negocio da
concessao, sem duplicar a logica de autorizacao.
"""

from sqlalchemy.exc import IntegrityError

from app.models.usuario import Usuario, utcnow
from app.models.usuario_caso import UsuarioCaso
from app.repositories.caso_repository import CasoRepository
from app.repositories.usuario_caso_repository import UsuarioCasoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.permissao import PermissaoCasoCreate
from app.services.caso_service import CasoNaoEncontradoError
from app.services.usuario_service import DadosInvalidosError, UsuarioNaoEncontradoError


class PermissaoJaExistenteError(Exception):
    """Concessao repetida para o mesmo usuario/caso (409)."""


class PermissaoNaoEncontradaError(Exception):
    """Nao ha concessao ativa para revogar (404)."""


class AutoConcessaoNegadaError(Exception):
    """Ninguem concede acesso a si mesmo (403)."""


class PermissaoCasoService:
    def __init__(
        self,
        permissoes: UsuarioCasoRepository,
        usuarios: UsuarioRepository,
        casos: CasoRepository,
    ):
        self.permissoes = permissoes
        self.usuarios = usuarios
        self.casos = casos

    def _caso_ou_erro(self, caso_id: int, admin: Usuario):
        caso = self.casos.buscar_visivel(caso_id, admin)
        if caso is None:
            raise CasoNaoEncontradoError("Caso nao encontrado")
        return caso

    def listar_do_caso(
        self, caso_id: int, admin: Usuario, *, incluir_revogados: bool = False
    ) -> list[UsuarioCaso]:
        self._caso_ou_erro(caso_id, admin)
        return self.permissoes.listar_por_caso(
            caso_id, incluir_revogados=incluir_revogados
        )

    def conceder(
        self, caso_id: int, dados: PermissaoCasoCreate, admin: Usuario
    ) -> UsuarioCaso:
        caso = self._caso_ou_erro(caso_id, admin)

        if dados.usuario_id == admin.id:
            raise AutoConcessaoNegadaError("Nao e possivel conceder acesso a si mesmo")
        if not dados.pode_visualizar:
            raise DadosInvalidosError("A concessao deve permitir a visualizacao do caso")

        alvo = self.usuarios.buscar_por_id(dados.usuario_id)
        if alvo is None:
            raise UsuarioNaoEncontradoError("Usuario nao encontrado")
        if not alvo.ativo:
            raise DadosInvalidosError(
                "Nao e possivel conceder acesso a usuario inativo"
            )

        existente = self.permissoes.buscar(alvo.id, caso.id)
        if existente is not None and existente.ativo:
            raise PermissaoJaExistenteError("Este usuario ja possui acesso a este caso")

        if existente is not None:
            # Reativa a MESMA linha (o UNIQUE impede segunda linha): o historico
            # de quem revogou/concedeu antes permanece na tabela.
            existente.ativo = True
            existente.pode_visualizar = dados.pode_visualizar
            existente.pode_registrar_andamento = dados.pode_registrar_andamento
            existente.pode_gerenciar_prazos = dados.pode_gerenciar_prazos
            existente.pode_gerenciar_processos = dados.pode_gerenciar_processos
            existente.pode_gerenciar_compromissos = dados.pode_gerenciar_compromissos
            existente.concedido_por = admin.id
            existente.concedido_em = utcnow()
            existente.revogado_por = None
            existente.revogado_em = None
            return self.permissoes.atualizar(existente)

        nova = UsuarioCaso(
            usuario_id=alvo.id,
            caso_id=caso.id,
            pode_visualizar=dados.pode_visualizar,
            pode_registrar_andamento=dados.pode_registrar_andamento,
            pode_gerenciar_prazos=dados.pode_gerenciar_prazos,
            pode_gerenciar_processos=dados.pode_gerenciar_processos,
            pode_gerenciar_compromissos=dados.pode_gerenciar_compromissos,
            ativo=True,
            concedido_por=admin.id,
        )
        try:
            return self.permissoes.criar(nova)
        except IntegrityError:
            # corrida entre o check acima e o INSERT (UNIQUE usuario_id+caso_id)
            self.permissoes.db.rollback()
            raise PermissaoJaExistenteError(
                "Este usuario ja possui acesso a este caso"
            )

    def revogar(self, caso_id: int, usuario_id: int, admin: Usuario) -> UsuarioCaso:
        self._caso_ou_erro(caso_id, admin)
        linha = self.permissoes.buscar(usuario_id, caso_id)
        if linha is None or not linha.ativo:
            raise PermissaoNaoEncontradaError(
                "Usuario nao possui acesso ativo a este caso"
            )
        # Revogacao soft: a linha fica com ativo=False para manter a
        # rastreabilidade de quem concedeu e de quem revogou.
        linha.ativo = False
        linha.revogado_por = admin.id
        linha.revogado_em = utcnow()
        return self.permissoes.atualizar(linha)
