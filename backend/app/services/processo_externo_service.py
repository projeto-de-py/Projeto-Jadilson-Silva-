"""Consulta de processos nos tribunais (DataJud/CNJ).

Fluxo: texto digitado -> NumeroCNJ (valida o formato e o digito verificador, descobre o
tribunal) -> DataJudClient (consulta o indice do tribunal) -> ConsultaProcesso.
"""

from dataclasses import dataclass

from app.integrations.datajud import DataJudClient, NumeroCNJ, ProcessoExterno


@dataclass(frozen=True)
class ConsultaProcesso:
    numero: str  # formatado: 0000000-00.0000.0.00.0000
    tribunal: str  # indice consultado, ex.: "tjba"
    instancias: list[ProcessoExterno]  # vazio = nao encontrado (ou segredo de justica)

    @property
    def encontrado(self) -> bool:
        return bool(self.instancias)


class ProcessoExternoService:
    def __init__(self, datajud: DataJudClient):
        self.datajud = datajud

    def consultar(self, numero_digitado: str) -> ConsultaProcesso:
        numero = NumeroCNJ.de_texto(numero_digitado)  # levanta DadosInvalidosError se nao servir
        return ConsultaProcesso(
            numero=numero.formatado,
            tribunal=numero.indice_datajud(),
            instancias=self.datajud.consultar(numero),
        )
