"""Service Layer: gerenciamento de prazos (Fase 4).

Regras principais:
- leitura: herda o escopo de visibilidade do caso (Fase 1) - um prazo fora do
  escopo responde 404, nunca revelando casos alheios;
- escrita (criar/editar/concluir/reabrir/cancelar): admin, advogado
  responsavel pelo caso ou usuario com a concessao `pode_gerenciar_prazos`
  ativa (mesmo padrao da Fase 3, com a permissao granular da Fase 1);
- caso arquivado nao recebe novos prazos; o processo vinculado precisa
  pertencer ao MESMO caso e nao pode estar arquivado (novo vinculo);
- responsavel precisa ser usuario ATIVO com acesso ao caso - nao ha escalada
  pelo payload: o status nasce PENDENTE e `concluido_*` so e preenchido na
  conclusao, pela rota propria;
- a situacao "vencido" e sempre CALCULADA (data local de Brasilia), nunca
  armazenada; nao ha calculo automatico de prazo processual (a data e
  informada manualmente pelo profissional);
- toda operacao relevante e registrada em `prazo_historicos` (auditoria);
- ATOMICIDADE: a alteracao do prazo e a sua auditoria compartilham UMA
  transacao (`_transacao`) - ou as duas persistem, ou nenhuma persiste.
"""

from contextlib import contextmanager
from datetime import date, datetime, timedelta
from typing import Any

from app.core.tempo import hoje_brasilia
from app.models.caso import Caso
from app.models.prazo import Prazo, StatusPrazo
from app.models.prazo_historico import (
    OP_CANCELAMENTO,
    OP_CONCLUSAO,
    OP_CRIACAO,
    OP_MUDANCA_RESPONSAVEL,
    OP_MUDANCA_VENCIMENTO,
    OP_ATUALIZACAO,
    OP_REABERTURA,
    PrazoHistorico,
)
from app.models.processo_judicial import ProcessoJudicial
from app.models.usuario import Usuario, utcnow
from app.repositories.caso_repository import CasoRepository
from app.repositories.prazo_historico_repository import PrazoHistoricoRepository
from app.repositories.prazo_repository import PrazoRepository
from app.repositories.processo_judicial_repository import ProcessoJudicialRepository
from app.repositories.usuario_caso_repository import UsuarioCasoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.prazo import PrazoCreate, PrazoUpdate
from app.services.caso_service import CasoNaoEncontradoError, ResponsavelInvalidoError
from app.services.cliente_service import DadosInvalidosError


class PrazoNaoEncontradoError(Exception):
    """Prazo inexistente ou fora do escopo do usuario (404)."""


class PrazoSemPermissaoError(Exception):
    """Operacao de escrita sem a permissao necessaria no caso (403)."""


class PrazoEstadoInvalidoError(Exception):
    """Transicao de status invalida (409)."""


class PrazoService:
    def __init__(
        self,
        prazos: PrazoRepository,
        historico: PrazoHistoricoRepository,
        casos: CasoRepository,
        permissoes: UsuarioCasoRepository,
        usuarios: UsuarioRepository,
        processos: ProcessoJudicialRepository,
    ):
        self.prazos = prazos
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
        prioridade: str | None = None,
        vencimento_de: date | None = None,
        vencimento_ate: date | None = None,
        vencidos: bool | None = None,
        pendentes: bool | None = None,
        concluidos: bool | None = None,
        pagina: int = 1,
        limite: int = 20,
    ) -> dict:
        """Lista paginada sob o escopo do usuario (filtros no banco)."""
        total, prazos = self.prazos.listar(
            usuario=usuario,
            q=q,
            caso_id=caso_id,
            processo_id=processo_id,
            responsavel_id=responsavel_id,
            tipo=tipo,
            status=status,
            prioridade=prioridade,
            vencimento_de=vencimento_de,
            vencimento_ate=vencimento_ate,
            vencidos=vencidos,
            pendentes=pendentes,
            concluidos=concluidos,
            pagina=pagina,
            limite=limite,
        )
        return {
            "itens": [self._serializar(p) for p in prazos],
            "total": total,
            "pagina": pagina,
            "limite": limite,
        }

    def buscar(self, prazo_id: int, usuario: Usuario) -> dict:
        prazo = self.prazos.buscar_visivel(prazo_id, usuario)
        if prazo is None:
            raise PrazoNaoEncontradoError("Prazo nao encontrado")
        return self._serializar(prazo)

    def listar_historico(self, prazo_id: int, usuario: Usuario) -> list[PrazoHistorico]:
        self.buscar(prazo_id, usuario)  # mesmo escopo do prazo
        return self.historico.listar_por_prazo(prazo_id)

    def listar_urgentes(
        self,
        usuario: Usuario,
        *,
        dias: int = 7,
        pagina: int = 1,
        limite: int = 20,
    ) -> dict:
        """Vencidos + vencem hoje + vencem nos proximos `dias` (Brasilia).

        So entram prazos em aberto (PENDENTE/EM_ANDAMENTO); a ordenacao
        respeita situacao, prioridade cadastrada e data.
        """
        hoje = hoje_brasilia()
        ate = hoje + timedelta(days=dias)
        total, rows = self.prazos.listar_urgentes(
            usuario=usuario, ate=ate, hoje=hoje, pagina=pagina, limite=limite
        )
        itens = []
        for prazo, numero, cliente in rows:
            item = self._serializar(prazo)
            if prazo.data_vencimento < hoje:
                situacao = "VENCIDO"
            elif prazo.data_vencimento == hoje:
                situacao = "HOJE"
            else:
                situacao = "PROXIMO"
            item.update(
                {"situacao": situacao, "numero_processo": numero, "cliente": cliente}
            )
            itens.append(item)
        return {
            "itens": itens,
            "total": total,
            "pagina": pagina,
            "limite": limite,
            "dias": dias,
        }

    # ------------------------------------------------------------- criacao

    def criar(self, dados: PrazoCreate, operador: Usuario) -> dict:
        caso = self._caso_ou_erro(dados.caso_id, operador)
        self._pode_gerenciar(caso, operador)

        if caso.arquivado:
            # um caso arquivado nao recebe novos prazos (mesma regra da Fase 3).
            raise DadosInvalidosError(
                "Nao e possivel adicionar prazo a um caso arquivado"
            )

        processo = None
        if dados.processo_id:
            processo = self._processo_valido(
                dados.processo_id, caso, operador, exigir_ativo=True
            )

        # Responsavel ausente = o proprio operador (nunca fica sem responsavel).
        responsavel_id = dados.responsavel_id or operador.id
        self._responsavel_valido(responsavel_id, caso)

        prazo = Prazo(
            caso_id=caso.id,
            processo_id=processo.id if processo else None,
            titulo=dados.titulo,
            descricao=dados.descricao,
            tipo=dados.tipo,
            data_inicio=dados.data_inicio,
            data_vencimento=dados.data_vencimento,
            status=StatusPrazo.PENDENTE.value,
            prioridade=dados.prioridade,
            responsavel_id=responsavel_id,
            observacoes=dados.observacoes,
            criado_por=operador.id,
        )
        with self._transacao():
            prazo = self.prazos.criar(prazo)
            self.historico.registrar(prazo.id, operador.id, OP_CRIACAO)
        return self._serializar(prazo)

    # ---------------------------------------------------------- atualizacao

    def atualizar(
        self, prazo_id: int, dados: PrazoUpdate, operador: Usuario
    ) -> dict:
        prazo, caso = self._buscar_para_edicao(prazo_id, operador)

        if prazo.status in (StatusPrazo.CONCLUIDO.value, StatusPrazo.CANCELADO.value):
            raise PrazoEstadoInvalidoError(
                "Prazo concluido/cancelado nao pode ser editado; reabra-o primeiro"
            )

        campos = dados.model_dump(exclude_unset=True)
        self._campos_obrigatorios(campos)

        if "processo_id" in campos and campos["processo_id"] is not None:
            processo = self._processo_valido(
                campos["processo_id"], caso, operador, exigir_ativo=True
            )
            campos["processo_id"] = processo.id
        if "responsavel_id" in campos and campos["responsavel_id"] is not None:
            self._responsavel_valido(campos["responsavel_id"], caso)

        inicio = campos.get("data_inicio", prazo.data_inicio)
        vencimento = campos.get("data_vencimento", prazo.data_vencimento)
        if inicio and vencimento and inicio > vencimento:
            raise DadosInvalidosError(
                "data_inicio nao pode ser posterior a data_vencimento"
            )

        alteracoes: dict[str, dict[str, Any]] = {}
        for campo, valor in campos.items():
            antes = getattr(prazo, campo)
            if antes == valor:
                continue
            setattr(prazo, campo, valor)
            alteracoes[campo] = {
                "antes": self._json(antes),
                "depois": self._json(valor),
            }

        if not alteracoes:
            return self._serializar(prazo)  # nada mudou: sem registro

        with self._transacao():
            self.prazos.atualizar(prazo)

            # Auditoria por categoria: uma entrada para cada tipo de mudanca.
            outros = {
                k: v
                for k, v in alteracoes.items()
                if k not in ("responsavel_id", "data_vencimento")
            }
            if outros:
                self.historico.registrar(prazo.id, operador.id, OP_ATUALIZACAO, outros)
            if "responsavel_id" in alteracoes:
                self.historico.registrar(
                    prazo.id,
                    operador.id,
                    OP_MUDANCA_RESPONSAVEL,
                    {"responsavel_id": alteracoes["responsavel_id"]},
                )
            if "data_vencimento" in alteracoes:
                self.historico.registrar(
                    prazo.id,
                    operador.id,
                    OP_MUDANCA_VENCIMENTO,
                    {"data_vencimento": alteracoes["data_vencimento"]},
                )
        return self._serializar(prazo)

    # --------------------------------------------------- transicoes de fim

    def concluir(self, prazo_id: int, operador: Usuario) -> dict:
        prazo, _ = self._buscar_para_edicao(prazo_id, operador)
        if prazo.status == StatusPrazo.CONCLUIDO.value:
            raise PrazoEstadoInvalidoError("Prazo ja esta concluido")
        if prazo.status == StatusPrazo.CANCELADO.value:
            raise PrazoEstadoInvalidoError(
                "Prazo cancelado nao pode ser concluido; reabra-o primeiro"
            )
        antes = prazo.status
        with self._transacao():
            prazo.status = StatusPrazo.CONCLUIDO.value
            prazo.concluido_em = utcnow()
            prazo.concluido_por = operador.id
            self.prazos.atualizar(prazo)
            self.historico.registrar(
                prazo.id,
                operador.id,
                OP_CONCLUSAO,
                {"status": {"antes": antes, "depois": prazo.status}},
            )
        return self._serializar(prazo)

    def reabrir(self, prazo_id: int, operador: Usuario) -> dict:
        prazo, _ = self._buscar_para_edicao(prazo_id, operador)
        if prazo.status not in (
            StatusPrazo.CONCLUIDO.value,
            StatusPrazo.CANCELADO.value,
        ):
            raise PrazoEstadoInvalidoError(
                "Prazo nao esta concluido nem cancelado"
            )
        antes = prazo.status
        with self._transacao():
            prazo.status = StatusPrazo.PENDENTE.value
            prazo.concluido_em = None
            prazo.concluido_por = None
            self.prazos.atualizar(prazo)
            self.historico.registrar(
                prazo.id,
                operador.id,
                OP_REABERTURA,
                {"status": {"antes": antes, "depois": prazo.status}},
            )
        return self._serializar(prazo)

    def cancelar(self, prazo_id: int, operador: Usuario) -> dict:
        prazo, _ = self._buscar_para_edicao(prazo_id, operador)
        if prazo.status == StatusPrazo.CANCELADO.value:
            raise PrazoEstadoInvalidoError("Prazo ja esta cancelado")
        if prazo.status == StatusPrazo.CONCLUIDO.value:
            raise PrazoEstadoInvalidoError(
                "Prazo concluido nao pode ser cancelado; reabra-o primeiro"
            )
        antes = prazo.status
        with self._transacao():
            prazo.status = StatusPrazo.CANCELADO.value
            self.prazos.atualizar(prazo)
            self.historico.registrar(
                prazo.id,
                operador.id,
                OP_CANCELAMENTO,
                {"status": {"antes": antes, "depois": prazo.status}},
            )
        return self._serializar(prazo)

    # ------------------------------------------------------------- privado

    @contextmanager
    def _transacao(self):
        """Uma unica transacao para o negocio E a auditoria do prazo.

        Nenhum commit intermediario: o `flush` dos repositories e o commit
        final acontecem aqui. Qualquer falha (inclusive no registro do
        historico) chama `rollback()`, desfazendo a alteracao do prazo junto -
        nao existe prazo alterado sem a sua trilha de auditoria.
        """
        try:
            yield
        except BaseException:
            self.prazos.desfazer()
            raise
        else:
            self.prazos.confirmar()

    def _buscar_para_edicao(
        self, prazo_id: int, operador: Usuario
    ) -> tuple[Prazo, Caso]:
        """Prazo + caso, com escopo (404) e permissao de escrita (403)."""
        prazo = self.prazos.buscar_visivel(prazo_id, operador)
        if prazo is None:
            raise PrazoNaoEncontradoError("Prazo nao encontrado")
        caso = self._caso_ou_erro(prazo.caso_id, operador)
        self._pode_gerenciar(caso, operador)
        return prazo, caso

    def _caso_ou_erro(self, caso_id: int, usuario: Usuario) -> Caso:
        """Caso acessivel ao usuario (escopo Fase 1) - senao 404."""
        caso = self.casos.buscar_visivel(caso_id, usuario, incluir_arquivados=True)
        if caso is None:
            raise CasoNaoEncontradoError("Caso nao encontrado")
        return caso

    def _pode_gerenciar(self, caso: Caso, operador: Usuario) -> None:
        """Admin, advogado responsavel pelo caso ou com `pode_gerenciar_prazos`."""
        if operador.administrador:
            return
        if caso.responsavel_id == operador.id:
            return
        linha = self.permissoes.buscar(operador.id, caso.id)
        if linha is not None and linha.ativo and linha.pode_gerenciar_prazos:
            return
        raise PrazoSemPermissaoError("Sem permissao para gerenciar prazos deste caso")

    def _processo_valido(
        self,
        processo_id: int,
        caso: Caso,
        usuario: Usuario,
        *,
        exigir_ativo: bool,
    ) -> ProcessoJudicial:
        """Processo existente, do mesmo caso e (para novo vinculo) nao arquivado."""
        processo = self.processos.buscar_visivel(
            processo_id, usuario, incluir_arquivados=True
        )
        if processo is None:
            raise DadosInvalidosError("Processo nao encontrado")
        if processo.caso_id != caso.id:
            raise DadosInvalidosError("Processo nao pertence ao caso informado")
        if exigir_ativo and processo.arquivado:
            raise DadosInvalidosError(
                "Processo arquivado nao recebe novos prazos"
            )
        return processo

    def _responsavel_valido(self, responsavel_id: int, caso: Caso | None) -> Usuario:
        """Responsavel ativo; com caso, precisa ter acesso a ele."""
        usuario = self.usuarios.buscar_por_id(responsavel_id)
        if usuario is None or not usuario.ativo:
            raise ResponsavelInvalidoError("Responsavel deve ser um usuario ativo")
        if caso is not None and not self._tem_acesso_ao_caso(usuario, caso):
            raise ResponsavelInvalidoError(
                "Responsavel nao tem acesso a este caso"
            )
        return usuario

    def _tem_acesso_ao_caso(self, usuario: Usuario, caso: Caso) -> bool:
        """Escopo de linha: admin, responsavel do caso ou concessao ativa."""
        if not usuario.ativo:
            return False
        if usuario.administrador:
            return True
        if caso.responsavel_id == usuario.id:
            return True
        linha = self.permissoes.buscar(usuario.id, caso.id)
        return linha is not None and linha.ativo and linha.pode_visualizar

    @staticmethod
    def _campos_obrigatorios(campos: dict[str, Any]) -> None:
        """Campos que podem ser enviados nulos no PATCH nao podem ser limpos."""
        if "titulo" in campos and campos["titulo"] is None:
            raise DadosInvalidosError("titulo e obrigatorio")
        if "data_vencimento" in campos and campos["data_vencimento"] is None:
            raise DadosInvalidosError("data_vencimento e obrigatoria")
        if "responsavel_id" in campos and campos["responsavel_id"] is None:
            raise DadosInvalidosError("informe um responsavel")

    @staticmethod
    def _serializar(prazo: Prazo) -> dict:
        """DTO do prazo; `vencido` e calculado (nunca armazenado)."""
        return {
            "id": prazo.id,
            "caso_id": prazo.caso_id,
            "processo_id": prazo.processo_id,
            "titulo": prazo.titulo,
            "descricao": prazo.descricao,
            "tipo": prazo.tipo,
            "data_inicio": prazo.data_inicio,
            "data_vencimento": prazo.data_vencimento,
            "status": prazo.status,
            "vencido": prazo.vencido,
            "prioridade": prazo.prioridade,
            "responsavel_id": prazo.responsavel_id,
            "responsavel_nome": prazo.responsavel_nome,
            "observacoes": prazo.observacoes,
            "concluido_em": prazo.concluido_em,
            "concluido_por": prazo.concluido_por,
            "criado_por": prazo.criado_por,
            "criado_em": prazo.criado_em,
            "atualizado_em": prazo.atualizado_em,
        }

    @staticmethod
    def _json(valor: Any) -> Any:
        if isinstance(valor, (date, datetime)):
            return valor.isoformat()
        return valor
