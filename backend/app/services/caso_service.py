"""Service Layer: gerenciamento de casos juridicos (Fase 2).

Regras principais:
- um caso NAO exige numero de processo judicial (demandas administrativas e
  extrajudiciais nao tem numero);
- criar: operador precisa ser advogado (gate `require_advogado` na rota) e o
  cliente precisa estar acessivel a ele (admin: qualquer cliente ativo;
  comum: cliente do escopo de visibilidade da Fase 1);
- responsavel: usuario ativo com perfil ADVOGADO; comum so pode assumir a
  propria responsabilidade (atribuir terceiros e exclusivo do admin);
- atualizar: admin ou o advogado responsavel pelo caso - funcionario nunca
  edita, mesmo com acesso;
- arquivamento: soft delete (admin), preservando todos os relacionamentos;
- toda operacao relevante e registrada em `caso_historicos` (auditoria).

A concessao de acesso criada automaticamente na criacao/atualizacao e
provisionamento rastreavel (concedido_por = operador), nao "concessao livre":
a proibicao de auto-concessao da Fase 1 vale para o endpoint de gestao de
permissoes, onde um usuario pediria acesso a casos que nao sao seus.
"""

from datetime import date
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.models.caso import Caso
from app.models.caso_historico import (
    OP_ARQUIVAMENTO,
    OP_ATUALIZACAO,
    OP_CRIACAO,
    CasoHistorico,
)
from app.models.usuario import Perfil, Usuario, utcnow
from app.models.usuario_caso import UsuarioCaso
from app.repositories.caso_historico_repository import CasoHistoricoRepository
from app.repositories.caso_repository import CasoRepository
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.usuario_caso_repository import UsuarioCasoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.caso import CasoCreate, CasoUpdate
from app.services.cliente_service import ClienteNaoEncontradoError, DadosInvalidosError
from app.repositories.notificacao_repository import NotificacaoRepository
from app.services.notificacao_service import GeradorNotificacaoCaso, NotificacaoService


class CasoNaoEncontradoError(Exception):
    """Caso inexistente OU sem permissao de acesso - ambos respondem 404.

    Usar o mesmo erro nos dois casos evita que um usuario descubra a
    existencia de casos de outros advogados trocando o id da URL.
    """


class ResponsavelInvalidoError(Exception):
    """Responsavel inexistente (404) ou inativo/nao-advogado (422)."""


class PermissaoEdicaoNegadaError(Exception):
    """Operacao de escrita negada (403)."""


class NumeroProcessoDuplicadoError(Exception):
    """Numero de processo ja cadastrado em outro caso (409)."""


class CasoJaArquivadoError(Exception):
    """Arquivamento repetido (409) - operacao idempotente recusada."""


def _serializar(valor: Any) -> Any:
    """Torna o valor gravavel em JSON no historico (datas em ISO)."""
    if isinstance(valor, (date,)):
        return valor.isoformat()
    return valor


class CasoService:
    def __init__(
        self,
        casos: CasoRepository,
        historico: CasoHistoricoRepository,
        clientes: ClienteRepository,
        usuarios: UsuarioRepository,
        permissoes: UsuarioCasoRepository,
    ):
        self.casos = casos
        self.historico = historico
        self.clientes = clientes
        self.usuarios = usuarios
        self.permissoes = permissoes

    # ------------------------------------------------------------- leitura

    def listar(self, usuario: Usuario, **filtros: Any) -> dict:
        itens, total = self.casos.listar(usuario=usuario, **filtros)
        return {
            "itens": itens,
            "total": total,
            "pagina": filtros.get("pagina", 1),
            "limite": filtros.get("limite", 20),
        }

    def buscar(self, caso_id: int, usuario: Usuario) -> Caso:
        # Arquivados continuam consultaveis por id (mantem o historico
        # acessivel), mas ficam fora das listagens padrao.
        caso = self.casos.buscar_visivel(caso_id, usuario, incluir_arquivados=True)
        if caso is None:
            raise CasoNaoEncontradoError("Caso nao encontrado")
        return caso

    def listar_historico(self, caso_id: int, usuario: Usuario) -> list[CasoHistorico]:
        self.buscar(caso_id, usuario)  # aplica o mesmo escopo de visibilidade
        return self.historico.listar_por_caso(caso_id)

    # ------------------------------------------------------------- criacao

    def criar(self, dados: CasoCreate, operador: Usuario) -> Caso:
        cliente = self._cliente_valido(dados.cliente_id, operador)

        if dados.responsavel_id is None:
            # padrao: o proprio operador assume - ja e validado como advogado
            # pelo gate da rota.
            responsavel = operador
        else:
            responsavel = self._responsavel_valido(dados.responsavel_id, operador)

        caso = Caso(
            titulo=dados.titulo.strip(),
            cliente_id=cliente.id,
            cliente=cliente.nome,  # espelho do cadastro (compat. frontend)
            numero_processo=(dados.numero_processo or "").strip() or None,
            area=dados.area,
            tipo_demanda=dados.tipo_demanda,
            status=dados.status,
            prioridade=dados.prioridade,
            data_abertura=dados.data_abertura or date.today(),
            responsavel_id=responsavel.id,
            parte_contraria=dados.parte_contraria,
            tribunal=dados.tribunal,
            vara=dados.vara,
            descricao=dados.descricao,
            observacoes=dados.observacoes,
            arquivado=False,
            criado_por=operador.id,
        )
        try:
            caso = self.casos.criar(caso)
        except IntegrityError:
            # unico UNIQUE de casos: numero_processo duplicado (corrida)
            self.casos.db.rollback()
            raise NumeroProcessoDuplicadoError(
                "Ja existe um caso com este numero de processo"
            )

        # Quem nasce com o caso precisa enxega-lo depois (sem isto, um advogado
        # comum criaria um caso que so o admin vera).
        self._garantir_acesso(caso, responsavel, operador)
        if operador.id != responsavel.id:
            self._garantir_acesso(caso, operador, operador)

        self.historico.registrar(caso.id, operador.id, OP_CRIACAO)
        if responsavel.id != operador.id:
            GeradorNotificacaoCaso(NotificacaoService(NotificacaoRepository(self.casos.db))).atribuido(responsavel.id, caso.id)
        return caso

    # -------------------------------------------------------- atualizacao

    def atualizar(self, caso_id: int, dados: CasoUpdate, operador: Usuario) -> Caso:
        caso = self.buscar(caso_id, operador)

        if not operador.administrador and caso.responsavel_id != operador.id:
            raise PermissaoEdicaoNegadaError(
                "Somente o advogado principal ou o advogado responsavel "
                "podem alterar este caso"
            )

        campos = dados.model_dump(exclude_unset=True)
        alteracoes: dict[str, dict[str, Any]] = {}

        def aplicar(campo: str, valor: Any) -> None:
            anterior = getattr(caso, campo)
            if anterior == valor:
                return
            setattr(caso, campo, valor)
            alteracoes[campo] = {
                "antes": _serializar(anterior),
                "depois": _serializar(valor),
            }

        if "cliente_id" in campos and campos["cliente_id"] != caso.cliente_id:
            cliente = self._cliente_valido(campos.pop("cliente_id"), operador)
            aplicar("cliente_id", cliente.id)
            aplicar("cliente", cliente.nome)  # mantem o espelho em dia

        if "responsavel_id" in campos and campos["responsavel_id"] != caso.responsavel_id:
            novo_id = campos.pop("responsavel_id")
            if novo_id is None:
                raise ResponsavelInvalidoError("Informe um advogado responsavel")
            responsavel = self._responsavel_valido(novo_id, operador)
            aplicar("responsavel_id", responsavel.id)
            # o novo responsavel precisa enxergar o caso
            self._garantir_acesso(caso, responsavel, operador)

        if campos.get("data_abertura") is not None and campos["data_abertura"] > date.today():
            raise DadosInvalidosError("Data de abertura nao pode ser no futuro")

        for campo, valor in campos.items():
            aplicar(campo, valor)

        if not alteracoes:
            return caso  # nada mudou: nao grava nem audita

        try:
            caso = self.casos.atualizar(caso)
        except IntegrityError:
            self.casos.db.rollback()
            raise NumeroProcessoDuplicadoError(
                "Ja existe um caso com este numero de processo"
            )

        self.historico.registrar(
            caso.id, operador.id, OP_ATUALIZACAO, alteracoes
        )
        return caso

    # -------------------------------------------------------- arquivamento

    def arquivar(self, caso_id: int, admin: Usuario) -> Caso:
        """Soft delete: preserva historico, prazos, andamentos e acessos."""
        caso = self.buscar(caso_id, admin)
        if caso.arquivado:
            raise CasoJaArquivadoError("Caso ja esta arquivado")

        caso.arquivado = True
        caso.arquivado_por = admin.id
        caso.arquivado_em = utcnow()
        caso = self.casos.atualizar(caso)

        self.historico.registrar(
            caso.id,
            admin.id,
            OP_ARQUIVAMENTO,
            {"arquivado": {"antes": False, "depois": True}},
        )
        return caso

    # ------------------------------------------------------------- privado

    def _cliente_valido(self, cliente_id: int, operador: Usuario):
        """Cliente acessivel ao operador e ativo (senao 404/422)."""
        if operador.administrador:
            cliente = self.clientes.buscar_por_id(cliente_id)
        else:
            # mesmo criterio da Fase 1: inexistente e inacessivel viram 404
            # para nao revelar cadastros de outros advogados.
            cliente = self.clientes.buscar_visivel(cliente_id, operador)
        if cliente is None:
            raise ClienteNaoEncontradoError("Cliente nao encontrado")
        if not cliente.ativo:
            raise DadosInvalidosError("Nao e possivel usar um cliente inativo")
        return cliente

    def _responsavel_valido(self, usuario_id: int, operador: Usuario) -> Usuario:
        """Advogado ativo; comum so pode ser responsavel por si mesmo."""
        if not operador.administrador and usuario_id != operador.id:
            raise PermissaoEdicaoNegadaError(
                "Apenas o advogado principal pode atribuir o caso a outro advogado"
            )
        usuario = self.usuarios.buscar_por_id(usuario_id)
        if usuario is None:
            raise ResponsavelInvalidoError("Advogado responsavel nao encontrado")
        if not usuario.ativo:
            raise ResponsavelInvalidoError(
                "Advogado responsavel precisa estar ativo"
            )
        if usuario.perfil != Perfil.ADVOGADO.value:
            raise ResponsavelInvalidoError(
                "Advogado responsavel precisa ter perfil ADVOGADO"
            )
        return usuario

    def _garantir_acesso(self, caso: Caso, alvo: Usuario, operador: Usuario) -> None:
        """Concede/reativa o acesso do responsavel/criador ao caso novo."""
        if alvo.administrador:
            return  # admin enxerga todos os casos - concessao e desnecessaria
        linha = self.permissoes.buscar(alvo.id, caso.id)
        if linha is not None and linha.ativo:
            return
        if linha is not None:
            # reativa a MESMA linha (UNIQUE impede duplicata) - historia fica
            linha.ativo = True
            linha.pode_visualizar = True
            linha.concedido_por = operador.id
            linha.concedido_em = utcnow()
            linha.revogado_por = None
            linha.revogado_em = None
            self.permissoes.atualizar(linha)
            return
        nova = UsuarioCaso(
            usuario_id=alvo.id,
            caso_id=caso.id,
            pode_visualizar=True,
            ativo=True,
            concedido_por=operador.id,
        )
        self.permissoes.criar(nova)
