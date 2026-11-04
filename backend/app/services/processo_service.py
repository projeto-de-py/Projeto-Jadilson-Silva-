"""Service Layer: gerenciamento de processos judiciais (Fase 3).

Regras principais:
- um processo e SEMPRE vinculado a um caso (caso_id vem da URL, nunca do
  payload) e exige numero CNJ valido (digitos verificadores);
- leitura: herda o escopo de visibilidade do caso (Fase 1) - um processo nao
  da acesso indireto a um caso nao autorizado;
- escrita (criar/editar/status/arquivar): admin, advogado responsavel pelo
  caso, ou usuario com a concessao `pode_gerenciar_processos` ativa. Funcionario
  so cadastra processo quando o admin lhe concedeu essa permissao;
- arquivamento e da PROCESSO (soft), distinto do arquivamento do caso;
- toda operacao relevante e registrada em `processo_historicos` (auditoria).

O numero CNJ e normalizado (20 digitos) antes de persistir, garantindo a
unicidade sobre a forma canonica.
"""

from datetime import date
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.core.validacao import (
    NumeroProcessoInvalidoError,
    normalizar_numero_processo,
)
from app.models.caso import Caso
from app.models.processo_historico import (
    OP_ARQUIVAMENTO,
    OP_ATUALIZACAO,
    OP_CRIACAO,
    OP_MUDANCA_STATUS,
    ProcessoHistorico,
)
from app.models.processo_judicial import ProcessoJudicial, STATUS_ENCERRADOS
from app.models.usuario import Usuario, utcnow
from app.models.usuario_caso import UsuarioCaso
from app.repositories.caso_repository import CasoRepository
from app.repositories.processo_historico_repository import ProcessoHistoricoRepository
from app.repositories.processo_judicial_repository import ProcessoJudicialRepository
from app.repositories.usuario_caso_repository import UsuarioCasoRepository
from app.schemas.processo import (
    ProcessoCreate,
    ProcessoStatusUpdate,
    ProcessoUpdate,
)
from app.services.caso_service import CasoNaoEncontradoError
from app.services.cliente_service import DadosInvalidosError


class ProcessoNaoEncontradoError(Exception):
    """Processo inexistente OU fora do escopo - ambos respondem 404."""


class ProcessoJaArquivadoError(Exception):
    """Arquivamento repetido (409)."""


class ProcessoSemPermissaoError(Exception):
    """Operacao de escrita negada (403)."""


class ProcessoNumeroDuplicadoError(Exception):
    """Numero CNJ ja cadastrado em outro processo (409)."""


def _serializar(valor: Any) -> Any:
    if isinstance(valor, date):
        return valor.isoformat()
    if hasattr(valor, "as_tuple"):  # Decimal (valor_causa)
        return float(valor)
    return valor


class ProcessoJudicialService:
    def __init__(
        self,
        processos: ProcessoJudicialRepository,
        historico: ProcessoHistoricoRepository,
        casos: CasoRepository,
        permissoes: UsuarioCasoRepository,
    ):
        self.processos = processos
        self.historico = historico
        self.casos = casos
        self.permissoes = permissoes

    # ------------------------------------------------------------- leitura

    def listar(self, usuario: Usuario, **filtros: Any) -> dict:
        itens, total = self.processos.listar(usuario=usuario, **filtros)
        return {
            "itens": itens,
            "total": total,
            "pagina": filtros.get("pagina", 1),
            "limite": filtros.get("limite", 20),
        }

    def listar_do_caso(
        self, caso_id: int, usuario: Usuario, *, arquivados: bool = False
    ) -> list[ProcessoJudicial]:
        self._caso_ou_erro(caso_id, usuario)  # garante escopo do caso (404)
        return self.processos.listar_por_caso(caso_id, usuario, arquivado=arquivados)

    def buscar(self, processo_id: int, usuario: Usuario) -> ProcessoJudicial:
        # Arquivados continuam consultaveis por id (historico preservado).
        processo = self.processos.buscar_visivel(
            processo_id, usuario, incluir_arquivados=True
        )
        if processo is None:
            raise ProcessoNaoEncontradoError("Processo nao encontrado")
        return processo

    def listar_historico(
        self, processo_id: int, usuario: Usuario
    ) -> list[ProcessoHistorico]:
        self.buscar(processo_id, usuario)  # mesmo escopo do processo
        return self.historico.listar_por_processo(processo_id)

    # ------------------------------------------------------------- criacao

    def criar(self, caso_id: int, dados: ProcessoCreate, operador: Usuario) -> ProcessoJudicial:
        caso = self._caso_ou_erro(caso_id, operador)
        self._pode_editar(caso, operador)

        if caso.arquivado:
            # um caso arquivado nao recebe novos processos (a demanda ja foi
            # encerrada/arquivada - reabrir e papel do admin).
            raise DadosInvalidosError("Nao e possivel adicionar processo a um caso arquivado")

        self._data_coerente(dados.data_distribuicao)
        numero = self._numero_valido(dados.numero_processo)
        if self.processos.existe_numero(numero):
            raise ProcessoNumeroDuplicadoError(
                "Ja existe um processo com este numero CNJ"
            )

        processo = ProcessoJudicial(
            caso_id=caso.id,
            numero_processo=numero,
            tribunal=dados.tribunal,
            orgao_julgador=dados.orgao_julgador,
            comarca=dados.comarca,
            instancia=dados.instancia,
            classe_processual=dados.classe_processual,
            assunto=dados.assunto,
            data_distribuicao=dados.data_distribuicao,
            status=dados.status,
            valor_causa=dados.valor_causa,
            segredo_justica=dados.segredo_justica,
            observacoes=dados.observacoes,
            arquivado=False,
            criado_por=operador.id,
        )
        try:
            processo = self.processos.criar(processo)
        except IntegrityError:
            self.processos.db.rollback()
            raise ProcessoNumeroDuplicadoError(
                "Ja existe um processo com este numero CNJ"
            )

        self.historico.registrar(processo.id, operador.id, OP_CRIACAO)
        return processo

    # -------------------------------------------------------- atualizacao

    def atualizar(self, processo_id: int, dados: ProcessoUpdate, operador: Usuario) -> ProcessoJudicial:
        processo = self.buscar(processo_id, operador)
        caso = self._caso_ou_erro(processo.caso_id, operador)
        self._pode_editar(caso, operador)

        campos = dados.model_dump(exclude_unset=True)
        alteracoes: dict[str, dict[str, Any]] = {}

        if "data_distribuicao" in campos:
            self._data_coerente(campos["data_distribuicao"])

        # numero: revalida e re-checa unicidade (nao pode colidir consigo mesmo)
        if "numero_processo" in campos:
            numero = self._numero_valido(campos["numero_processo"])
            if numero != processo.numero_processo and self.processos.existe_numero(numero):
                raise ProcessoNumeroDuplicadoError(
                    "Ja existe um processo com este numero CNJ"
                )
            campos["numero_processo"] = numero

        def aplicar(campo: str, valor: Any) -> None:
            anterior = getattr(processo, campo)
            if anterior == valor:
                return
            setattr(processo, campo, valor)
            alteracoes[campo] = {"antes": _serializar(anterior), "depois": _serializar(valor)}

        for campo, valor in campos.items():
            aplicar(campo, valor)

        if not alteracoes:
            return processo  # nada mudou: nao grava nem audita

        try:
            processo = self.processos.atualizar(processo)
        except IntegrityError:
            self.processos.db.rollback()
            raise ProcessoNumeroDuplicadoError(
                "Ja existe um processo com este numero CNJ"
            )

        self.historico.registrar(processo.id, operador.id, OP_ATUALIZACAO, alteracoes)
        return processo

    def mudar_status(
        self, processo_id: int, dados: ProcessoStatusUpdate, operador: Usuario
    ) -> ProcessoJudicial:
        """Mudanca explicita de situacao (inclui encerramento BAIXADO/EXTINTO)."""
        processo = self.buscar(processo_id, operador)
        caso = self._caso_ou_erro(processo.caso_id, operador)
        self._pode_editar(caso, operador)

        if processo.status == dados.status:
            return processo  # sem mudanca: nao audita

        anterior = processo.status
        processo.status = dados.status
        processo = self.processos.atualizar(processo)
        self.historico.registrar(
            processo.id,
            operador.id,
            OP_MUDANCA_STATUS,
            {"status": {"antes": anterior, "depois": dados.status}},
        )
        return processo

    # -------------------------------------------------------- arquivamento

    def arquivar(self, processo_id: int, operador: Usuario) -> ProcessoJudicial:
        """Soft delete do PROCESSO: preserva historico e vinculo com o caso."""
        processo = self.buscar(processo_id, operador)
        caso = self._caso_ou_erro(processo.caso_id, operador)
        self._pode_editar(caso, operador)

        if processo.arquivado:
            raise ProcessoJaArquivadoError("Processo ja esta arquivado")

        processo.arquivado = True
        processo.arquivado_por = operador.id
        processo.arquivado_em = utcnow()
        processo = self.processos.atualizar(processo)
        self.historico.registrar(
            processo.id,
            operador.id,
            OP_ARQUIVAMENTO,
            {"arquivado": {"antes": False, "depois": True}},
        )
        return processo

    # ------------------------------------------------------------- privado

    def _caso_ou_erro(self, caso_id: int, usuario: Usuario) -> Caso:
        """Caso acessivel ao usuario (escopo Fase 1) - senao 404."""
        caso = self.casos.buscar_visivel(caso_id, usuario, incluir_arquivados=True)
        if caso is None:
            raise CasoNaoEncontradoError("Caso nao encontrado")
        return caso

    def _pode_editar(self, caso: Caso, operador: Usuario) -> None:
        """Admin, advogado responsavel pelo caso ou com `pode_gerenciar_processos`."""
        if operador.administrador:
            return
        if caso.responsavel_id == operador.id:
            return
        linha = self.permissoes.buscar(operador.id, caso.id)
        if linha is not None and linha.ativo and linha.pode_gerenciar_processos:
            return
        raise ProcessoSemPermissaoError(
            "Sem permissao para gerenciar processos deste caso"
        )

    def _numero_valido(self, valor: str) -> str:
        """Normaliza e valida o numero CNJ (digitos verificadores)."""
        try:
            numero = normalizar_numero_processo(valor)
        except NumeroProcessoInvalidoError as exc:
            raise DadosInvalidosError(str(exc))
        if numero is None:
            raise DadosInvalidosError("Informe o numero do processo (CNJ)")
        return numero

    def _data_coerente(self, valor: date | None) -> None:
        """Data de distribuicao passada: acontece no protocolo, nunca no futuro."""
        if valor is not None and valor > date.today():
            raise DadosInvalidosError(
                "Data de distribuicao nao pode ser posterior a hoje"
            )


# re-export para as rotas
__all__ = [
    "ProcessoJudicialService",
    "ProcessoNaoEncontradoError",
    "ProcessoJaArquivadoError",
    "ProcessoSemPermissaoError",
    "ProcessoNumeroDuplicadoError",
    "STATUS_ENCERRADOS",
]
