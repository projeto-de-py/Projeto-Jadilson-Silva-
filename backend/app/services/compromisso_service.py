"""Service Layer: compromissos de agenda (Fase 4).

Regras principais:
- compromisso NUNCA e um `Prazo`: entidade propria com horarios de inicio/fim;
- leitura: compromissos COM caso herdam o escopo da Fase 1; compromissos SEM
  caso pertencem apenas ao administrador (a agenda nunca fica publica);
- escrita: para compromisso com caso - admin, responsavel do caso ou com a
  concessao `pode_gerenciar_compromissos` (permissao PROPRIA da Fase 4;
  `pode_gerenciar_prazos` NAO autoriza compromissos); compromisso SEM caso -
  somente o administrador;
- `data_fim` sempre posterior a `data_inicio` (validado no schema e no
  service apos o merge do PATCH); `processo_id` exige `caso_id` e o processo
  precisa pertencer ao mesmo caso;
- responsavel precisa ser usuario ATIVO (e com acesso ao caso quando houver);
  o status nasce AGENDADO e muda apenas pela rota `/status` - nao ha escalada
  pelo payload;
- horarios sao gravados em HORARIO LOCAL do escritorio (Brasilia);
- toda operacao relevante e registrada em `compromisso_historicos`;
- ATOMICIDADE: a alteracao do compromisso e a sua auditoria compartilham UMA
  transacao (`_transacao`) - ou as duas persistem, ou nenhuma persiste.
"""

from contextlib import contextmanager
from datetime import date, datetime
from typing import Any

from app.models.caso import Caso
from app.models.compromisso import Compromisso, StatusCompromisso
from app.models.compromisso_historico import (
    OP_ATUALIZACAO,
    OP_CANCELAMENTO,
    OP_CRIACAO,
    OP_MUDANCA_RESPONSAVEL,
    CompromissoHistorico,
)
from app.models.usuario import Usuario
from app.repositories.caso_repository import CasoRepository
from app.repositories.compromisso_historico_repository import (
    CompromissoHistoricoRepository,
)
from app.repositories.compromisso_repository import CompromissoRepository
from app.repositories.processo_judicial_repository import ProcessoJudicialRepository
from app.repositories.usuario_caso_repository import UsuarioCasoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.compromisso import (
    CompromissoCreate,
    CompromissoStatusUpdate,
    CompromissoUpdate,
)
from app.services.caso_service import CasoNaoEncontradoError, ResponsavelInvalidoError
from app.services.cliente_service import DadosInvalidosError


class CompromissoNaoEncontradoError(Exception):
    """Compromisso inexistente ou fora do escopo do usuario (404)."""


class CompromissoSemPermissaoError(Exception):
    """Operacao de escrita sem permissao no caso ou fora do perfil admin (403)."""


class CompromissoEstadoInvalidoError(Exception):
    """Transicao de status invalida (409)."""


class CompromissoService:
    def __init__(
        self,
        compromissos: CompromissoRepository,
        historico: CompromissoHistoricoRepository,
        casos: CasoRepository,
        permissoes: UsuarioCasoRepository,
        usuarios: UsuarioRepository,
        processos: ProcessoJudicialRepository,
    ):
        self.compromissos = compromissos
        self.historico = historico
        self.casos = casos
        self.permissoes = permissoes
        self.usuarios = usuarios
        self.processos = processos

    # ------------------------------------------------------------- leitura

    def listar(
        self,
        usuario: Usuario,
        *,
        q: str | None = None,
        caso_id: int | None = None,
        processo_id: int | None = None,
        responsavel_id: int | None = None,
        tipo: str | None = None,
        status: str | None = None,
        inicio_de: date | None = None,
        inicio_ate: date | None = None,
        pagina: int = 1,
        limite: int = 20,
    ) -> dict:
        total, itens = self.compromissos.listar(
            usuario=usuario,
            q=q,
            caso_id=caso_id,
            processo_id=processo_id,
            responsavel_id=responsavel_id,
            tipo=tipo,
            status=status,
            inicio_de=inicio_de,
            inicio_ate=inicio_ate,
            pagina=pagina,
            limite=limite,
        )
        return {
            "itens": [self._serializar(c) for c in itens],
            "total": total,
            "pagina": pagina,
            "limite": limite,
        }

    def agenda(
        self,
        usuario: Usuario,
        *,
        de: date,
        ate: date,
        responsavel_id: int | None = None,
        pagina: int = 1,
        limite: int = 50,
    ) -> dict:
        """Compromissos do periodo em ordem de horario (sem misturar prazos)."""
        if ate < de:
            raise DadosInvalidosError("Periodo invalido: 'ate' anterior a 'de'")
        if (ate - de).days > 366:
            raise DadosInvalidosError(
                "Periodo da agenda limitado a 366 dias"
            )
        total, itens = self.compromissos.listar_agenda(
            usuario=usuario,
            de=de,
            ate=ate,
            responsavel_id=responsavel_id,
            pagina=pagina,
            limite=limite,
        )
        return {
            "itens": [self._serializar(c) for c in itens],
            "total": total,
            "pagina": pagina,
            "limite": limite,
            "de": de,
            "ate": ate,
        }

    def buscar(self, compromisso_id: int, usuario: Usuario) -> dict:
        compromisso = self.compromissos.buscar_visivel(compromisso_id, usuario)
        if compromisso is None:
            raise CompromissoNaoEncontradoError("Compromisso nao encontrado")
        return self._serializar(compromisso)

    def listar_historico(
        self, compromisso_id: int, usuario: Usuario
    ) -> list[CompromissoHistorico]:
        self.buscar(compromisso_id, usuario)  # mesmo escopo
        return self.historico.listar_por_compromisso(compromisso_id)

    # ------------------------------------------------------------- criacao

    def criar(self, dados: CompromissoCreate, operador: Usuario) -> dict:
        caso: Caso | None = None
        if dados.caso_id:
            caso = self._caso_ou_erro(dados.caso_id, operador)
            self._pode_gerenciar(caso, operador)
            if caso.arquivado:
                raise DadosInvalidosError(
                    "Nao e possivel adicionar compromisso a um caso arquivado"
                )
            if dados.processo_id:
                self._processo_do_caso(dados.processo_id, caso, operador)
        elif not operador.administrador:
            # Compromisso sem caso nao pertence a nenhuma demanda: so o
            # advogado principal o cria/enxerga.
            raise CompromissoSemPermissaoError(
                "Compromissos sem caso sao restritos ao administrador"
            )

        responsavel_id = dados.responsavel_id or operador.id
        self._responsavel_valido(responsavel_id, caso)

        compromisso = Compromisso(
            caso_id=caso.id if caso else None,
            processo_id=dados.processo_id,
            titulo=dados.titulo,
            descricao=dados.descricao,
            tipo=dados.tipo,
            data_inicio=dados.data_inicio,
            data_fim=dados.data_fim,
            local=dados.local,
            responsavel_id=responsavel_id,
            status=StatusCompromisso.AGENDADO.value,
            criado_por=operador.id,
        )
        with self._transacao():
            compromisso = self.compromissos.criar(compromisso)
            self.historico.registrar(compromisso.id, operador.id, OP_CRIACAO)
        return self._serializar(compromisso)

    # ---------------------------------------------------------- atualizacao

    def atualizar(
        self, compromisso_id: int, dados: CompromissoUpdate, operador: Usuario
    ) -> dict:
        compromisso = self._buscar_para_edicao(compromisso_id, operador)
        caso = (
            self._caso_ou_erro(compromisso.caso_id, operador)
            if compromisso.caso_id
            else None
        )
        campos = dados.model_dump(exclude_unset=True)

        if "titulo" in campos and campos["titulo"] is None:
            raise DadosInvalidosError("titulo e obrigatorio")
        if "responsavel_id" in campos and campos["responsavel_id"] is None:
            raise DadosInvalidosError("informe um responsavel")

        if "responsavel_id" in campos and campos["responsavel_id"] is not None:
            self._responsavel_valido(campos["responsavel_id"], caso)

        # Coerencia do periodo com o resultado do merge (inicio e fim).
        inicio = campos.get("data_inicio", compromisso.data_inicio)
        fim = campos.get("data_fim", compromisso.data_fim)
        if inicio and fim and fim <= inicio:
            raise DadosInvalidosError("data_fim deve ser posterior a data_inicio")

        alteracoes: dict[str, dict[str, Any]] = {}
        for campo, valor in campos.items():
            antes = getattr(compromisso, campo)
            if antes == valor:
                continue
            setattr(compromisso, campo, valor)
            alteracoes[campo] = {
                "antes": self._json(antes),
                "depois": self._json(valor),
            }

        if not alteracoes:
            return self._serializar(compromisso)

        with self._transacao():
            self.compromissos.atualizar(compromisso)

            outros = {
                k: v for k, v in alteracoes.items() if k != "responsavel_id"
            }
            if outros:
                self.historico.registrar(
                    compromisso.id, operador.id, OP_ATUALIZACAO, outros
                )
            if "responsavel_id" in alteracoes:
                self.historico.registrar(
                    compromisso.id,
                    operador.id,
                    OP_MUDANCA_RESPONSAVEL,
                    {"responsavel_id": alteracoes["responsavel_id"]},
                )
        return self._serializar(compromisso)

    def alterar_status(
        self, compromisso_id: int, dados: CompromissoStatusUpdate, operador: Usuario
    ) -> dict:
        compromisso = self._buscar_para_edicao(compromisso_id, operador)
        if compromisso.status == dados.status:
            return self._serializar(compromisso)  # sem mudanca: sem auditoria

        antes = compromisso.status
        with self._transacao():
            compromisso.status = dados.status
            self.compromissos.atualizar(compromisso)

            # Cancelamento tem operacao propria; os demais viram ATUALIZACAO.
            operacao = (
                OP_CANCELAMENTO
                if dados.status == StatusCompromisso.CANCELADO.value
                else OP_ATUALIZACAO
            )
            self.historico.registrar(
                compromisso.id,
                operador.id,
                operacao,
                {"status": {"antes": antes, "depois": compromisso.status}},
            )
        return self._serializar(compromisso)

    # ------------------------------------------------------------- privado

    @contextmanager
    def _transacao(self):
        """Uma unica transacao para o negocio E a auditoria do compromisso.

        Sem commit intermediario: ou a alteracao e o registro em
        `compromisso_historicos` persistem juntos, ou o `rollback()` desfaz
        os dois.
        """
        try:
            yield
        except BaseException:
            self.compromissos.desfazer()
            raise
        else:
            self.compromissos.confirmar()

    def _buscar_para_edicao(
        self, compromisso_id: int, operador: Usuario
    ) -> Compromisso:
        """Compromisso com escopo (404) e permissao de escrita (403)."""
        compromisso = self.compromissos.buscar_visivel(compromisso_id, operador)
        if compromisso is None:
            raise CompromissoNaoEncontradoError("Compromisso nao encontrado")

        if compromisso.caso_id is None:
            if not operador.administrador:
                raise CompromissoSemPermissaoError(
                    "Compromissos sem caso sao restritos ao administrador"
                )
            return compromisso

        caso = self._caso_ou_erro(compromisso.caso_id, operador)
        self._pode_gerenciar(caso, operador)
        return compromisso

    def _caso_ou_erro(self, caso_id: int, usuario: Usuario) -> Caso:
        caso = self.casos.buscar_visivel(caso_id, usuario, incluir_arquivados=True)
        if caso is None:
            raise CasoNaoEncontradoError("Caso nao encontrado")
        return caso

    def _pode_gerenciar(self, caso: Caso, operador: Usuario) -> None:
        """Admin, responsavel do caso ou com `pode_gerenciar_compromissos`.

        A permissao de compromissos e PROPRIA: `pode_gerenciar_prazos` nao
        concede autorizacao implicita sobre a agenda.
        """
        if operador.administrador:
            return
        if caso.responsavel_id == operador.id:
            return
        linha = self.permissoes.buscar(operador.id, caso.id)
        if linha is not None and linha.ativo and linha.pode_gerenciar_compromissos:
            return
        raise CompromissoSemPermissaoError(
            "Sem permissao para gerenciar compromissos deste caso"
        )

    def _processo_do_caso(
        self, processo_id: int, caso: Caso, usuario: Usuario
    ) -> None:
        """Processo existente e do mesmo caso (arquivamento nao bloqueia agenda)."""
        processo = self.processos.buscar_visivel(
            processo_id, usuario, incluir_arquivados=True
        )
        if processo is None:
            raise DadosInvalidosError("Processo nao encontrado")
        if processo.caso_id != caso.id:
            raise DadosInvalidosError("Processo nao pertence ao caso informado")

    def _responsavel_valido(
        self, responsavel_id: int, caso: Caso | None
    ) -> Usuario:
        usuario = self.usuarios.buscar_por_id(responsavel_id)
        if usuario is None or not usuario.ativo:
            raise ResponsavelInvalidoError("Responsavel deve ser um usuario ativo")
        if caso is not None and not self._tem_acesso_ao_caso(usuario, caso):
            raise ResponsavelInvalidoError("Responsavel nao tem acesso a este caso")
        return usuario

    def _tem_acesso_ao_caso(self, usuario: Usuario, caso: Caso) -> bool:
        if not usuario.ativo:
            return False
        if usuario.administrador:
            return True
        if caso.responsavel_id == usuario.id:
            return True
        linha = self.permissoes.buscar(usuario.id, caso.id)
        return linha is not None and linha.ativo and linha.pode_visualizar

    @staticmethod
    def _serializar(compromisso: Compromisso) -> dict:
        return {
            "id": compromisso.id,
            "caso_id": compromisso.caso_id,
            "processo_id": compromisso.processo_id,
            "titulo": compromisso.titulo,
            "descricao": compromisso.descricao,
            "tipo": compromisso.tipo,
            "data_inicio": compromisso.data_inicio,
            "data_fim": compromisso.data_fim,
            "local": compromisso.local,
            "responsavel_id": compromisso.responsavel_id,
            "responsavel_nome": compromisso.responsavel_nome,
            "status": compromisso.status,
            "processo_numero": compromisso.processo_numero,
            "criado_por": compromisso.criado_por,
            "criado_em": compromisso.criado_em,
            "atualizado_em": compromisso.atualizado_em,
        }

    @staticmethod
    def _json(valor: Any) -> Any:
        if isinstance(valor, (date, datetime)):
            return valor.isoformat()
        return valor
