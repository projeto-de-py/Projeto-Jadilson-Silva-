"""Service Layer: andamentos do caso (registro manual e importacao do tribunal pelo DataJud).

O escopo de acesso e o do proprio caso: quem nao enxerga o caso recebe 404, igual aos prazos.
"""

import hashlib
from dataclasses import dataclass
from datetime import datetime, time, timezone

from app.integrations.datajud import Movimento, ProcessoExterno
from app.models.andamento import ORIGEM_DATAJUD, ORIGEM_MANUAL, Andamento
from app.models.caso import Caso
from app.models.usuario import Usuario
from app.repositories.andamento_repository import AndamentoRepository
from app.schemas.andamento import AndamentoCreate
from app.services.caso_service import CasoService
from app.services.processo_externo_service import ProcessoExternoService


class AndamentoNaoEncontradoError(Exception):
    """Andamento inexistente neste caso (404)."""


class AndamentoDoTribunalError(Exception):
    """Andamentos importados do tribunal nao se apagam: sao o historico oficial (409)."""


class CasoSemNumeroError(Exception):
    """O caso nao tem numero CNJ, entao nao ha o que consultar no tribunal (422)."""


@dataclass(frozen=True)
class ResultadoSincronizacao:
    numero: str
    tribunal: str
    encontrado: bool
    novos: int
    ja_existentes: int

    @property
    def mensagem(self) -> str:
        if not self.encontrado:
            return "Processo não encontrado no DataJud (pode estar em segredo de justiça ou ainda não indexado)."
        if self.novos:
            return f"{self.novos} {'andamento novo importado' if self.novos == 1 else 'andamentos novos importados'}."
        return "Nada novo: o histórico já está atualizado."


def _sem_fuso(momento: datetime) -> datetime:
    """O banco guarda horario em UTC, sem fuso."""
    return momento.astimezone(timezone.utc).replace(tzinfo=None) if momento.tzinfo else momento


def _chave(instancia: ProcessoExterno, movimento: Movimento) -> str:
    bruto = f"{instancia.tribunal}|{instancia.grau}|{movimento.data.isoformat()}|{movimento.nome}|{movimento.complemento}"
    return hashlib.sha1(bruto.encode("utf-8")).hexdigest()


def _descricao(instancia: ProcessoExterno, movimento: Movimento) -> str:
    local = " · ".join(parte for parte in (instancia.grau, instancia.orgao_julgador) if parte)
    return "\n".join(parte for parte in (movimento.complemento, local) if parte)


class AndamentoService:
    def __init__(self, casos: CasoService, andamentos: AndamentoRepository, processos: ProcessoExternoService):
        self.casos = casos
        self.andamentos = andamentos
        self.processos = processos

    def listar(self, caso_id: int, usuario: Usuario, limite: int = 200) -> list[Andamento]:
        self.casos.buscar(caso_id, usuario)
        return self.andamentos.listar(caso_id, limite)

    def criar(self, caso_id: int, dados: AndamentoCreate, usuario: Usuario) -> Andamento:
        self.casos.buscar(caso_id, usuario)
        ocorrido = datetime.combine(dados.ocorrido_em, time.min) if dados.ocorrido_em else datetime.now(timezone.utc).replace(tzinfo=None)
        return self.andamentos.criar(
            Andamento(
                caso_id=caso_id,
                titulo=dados.titulo.strip(),
                descricao=(dados.descricao or "").strip() or None,
                ocorrido_em=ocorrido,
                criado_por_id=usuario.id,
                origem=ORIGEM_MANUAL,
            )
        )

    def excluir(self, caso_id: int, andamento_id: int, usuario: Usuario) -> None:
        self.casos.buscar(caso_id, usuario)
        andamento = self.andamentos.buscar(caso_id, andamento_id)
        if andamento is None:
            raise AndamentoNaoEncontradoError("Andamento não encontrado")
        if andamento.origem == ORIGEM_DATAJUD:
            raise AndamentoDoTribunalError("Andamentos importados do tribunal não podem ser apagados.")
        self.andamentos.excluir(andamento)

    def sincronizar(self, caso_id: int, usuario: Usuario) -> ResultadoSincronizacao:
        """Busca as movimentacoes no DataJud e grava so as que ainda nao existem."""
        caso: Caso = self.casos.buscar(caso_id, usuario)
        if not caso.numero_processo:
            raise CasoSemNumeroError("Este caso não tem número de processo (CNJ) para consultar no tribunal.")

        consulta = self.processos.consultar(caso.numero_processo)
        conhecidas = self.andamentos.chaves_externas(caso_id)
        novos: list[Andamento] = []
        for instancia in consulta.instancias:
            for movimento in instancia.movimentos:
                if movimento.data is None:
                    continue
                chave = _chave(instancia, movimento)
                if chave in conhecidas:
                    continue
                conhecidas.add(chave)
                novos.append(
                    Andamento(
                        caso_id=caso_id,
                        titulo=movimento.nome[:160],
                        descricao=_descricao(instancia, movimento) or None,
                        ocorrido_em=_sem_fuso(movimento.data),
                        criado_por_id=usuario.id,
                        origem=ORIGEM_DATAJUD,
                        chave_externa=chave,
                    )
                )
        if novos:
            self.andamentos.criar_varios(novos)
        return ResultadoSincronizacao(
            numero=consulta.numero,
            tribunal=consulta.tribunal,
            encontrado=consulta.encontrado,
            novos=len(novos),
            ja_existentes=len(conhecidas) - len(novos),
        )

