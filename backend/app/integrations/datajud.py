"""DataJud (CNJ): andamentos de processos judiciais.

API publica do Conselho Nacional de Justica. Cada tribunal tem seu proprio "indice":

    POST https://api-publica.datajud.cnj.jus.br/api_publica_<tribunal>/_search
    Authorization: APIKey <chave publica>
    corpo: {"query": {"match": {"numeroProcesso": "<20 digitos>"}}}

A chave publica e divulgada (e as vezes trocada) pelo CNJ em
https://datajud-wiki.cnj.jus.br/api-publica/acesso : coloque em DATAJUD_API_KEY no .env.
O DataJud traz dados e movimentacoes, NAO o inteiro teor, e nao mostra processos em
segredo de justica.

Este arquivo tem duas classes:
- NumeroCNJ        valida o numero do processo e descobre QUAL tribunal consultar;
- DataJudClient    faz a consulta e devolve dataclasses.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from app.integrations.base import ClienteHttp
from app.integrations.cache import CacheTTL
from app.integrations.erros import DadosInvalidosError, IntegracaoErro

MINUTO = 60

# Codigo do tribunal (campo TR do numero CNJ) -> sigla da UF, para a Justica Estadual (J=8).
_UF_POR_CODIGO = {
    1: "ac", 2: "al", 3: "ap", 4: "am", 5: "ba", 6: "ce", 7: "dft", 8: "es", 9: "go", 10: "ma",
    11: "mt", 12: "ms", 13: "mg", 14: "pa", 15: "pb", 16: "pr", 17: "pe", 18: "pi", 19: "rj",
    20: "rn", 21: "rs", 22: "ro", 23: "rr", 24: "sc", 25: "se", 26: "sp", 27: "to",
}


@dataclass(frozen=True)
class NumeroCNJ:
    """Numero unico de processo (Resolucao CNJ 65/2008): NNNNNNN-DD.AAAA.J.TR.OOOO.

    Use `NumeroCNJ.de_texto(...)`: ele valida o formato E o digito verificador, e levanta
    DadosInvalidosError com mensagem clara (sem gastar uma chamada a API).
    """

    sequencial: str  # NNNNNNN (7)
    digito: str  # DD (2)
    ano: str  # AAAA (4)
    justica: str  # J (1)
    tribunal: str  # TR (2)
    origem: str  # OOOO (4)

    @classmethod
    def de_texto(cls, texto: str) -> "NumeroCNJ":
        limpo = re.sub(r"\D", "", texto or "")
        if len(limpo) != 20:
            raise DadosInvalidosError("DataJud", "O número do processo precisa ter 20 dígitos (formato CNJ: 0000000-00.0000.0.00.0000).")
        n = cls(limpo[:7], limpo[7:9], limpo[9:13], limpo[13], limpo[14:16], limpo[16:20])
        if n.digito_esperado() != n.digito:
            raise DadosInvalidosError("DataJud", "Número de processo inválido: o dígito verificador não confere.")
        return n

    def digito_esperado(self) -> str:
        """DD = 98 - ((NNNNNNN AAAA J TR OOOO 00) mod 97)."""
        base = int(self.sequencial + self.ano + self.justica + self.tribunal + self.origem + "00")
        return f"{98 - (base % 97):02d}"

    @property
    def digitos(self) -> str:
        return self.sequencial + self.digito + self.ano + self.justica + self.tribunal + self.origem

    @property
    def formatado(self) -> str:
        return f"{self.sequencial}-{self.digito}.{self.ano}.{self.justica}.{self.tribunal}.{self.origem}"

    def indice_datajud(self) -> str:
        """Nome do indice do tribunal no DataJud (ex.: 'tjba', 'trt5', 'trf1')."""
        tr = int(self.tribunal)
        if self.justica == "8":  # Justica Estadual
            uf = _UF_POR_CODIGO.get(tr)
            if uf:
                return f"tj{uf}"
        elif self.justica == "5":  # Justica do Trabalho
            return "tst" if tr == 0 else f"trt{tr}" if 1 <= tr <= 24 else self._nao_suportado()
        elif self.justica == "4":  # Justica Federal
            return f"trf{tr}" if 1 <= tr <= 6 else self._nao_suportado()
        elif self.justica == "3" and tr == 0:
            return "stj"
        return self._nao_suportado()

    def _nao_suportado(self) -> str:
        raise DadosInvalidosError(
            "DataJud",
            "Este tribunal ainda não é consultado pelo sistema (suportados: Justiça Estadual, do Trabalho, Federal e STJ).",
        )


@dataclass(frozen=True)
class Movimento:
    data: datetime | None
    nome: str
    complemento: str = ""


@dataclass(frozen=True)
class ProcessoExterno:
    """Um processo (uma instancia/grau) como o DataJud informa."""

    numero: str
    tribunal: str
    grau: str
    classe: str
    assuntos: tuple[str, ...]
    orgao_julgador: str
    data_ajuizamento: datetime | None
    movimentos: tuple[Movimento, ...] = field(default_factory=tuple)  # do mais recente ao mais antigo


class DataJudClient(ClienteHttp):
    """Cliente do DataJud. Sem a chave publica configurada, levanta IntegracaoNaoConfiguradaError."""

    servico = "DataJud"
    MAX_MOVIMENTOS = 100

    def __init__(
        self,
        api_key: str | None,
        base_url: str = "https://api-publica.datajud.cnj.jus.br",
        *,
        http: httpx.Client | None = None,
        timeout: float = 25.0,
        cache: CacheTTL | None = None,
    ) -> None:
        super().__init__(base_url, http=http, timeout=timeout, cache=cache)
        self._key = api_key

    def _cabecalhos(self) -> dict:
        if not self._key:
            raise self._nao_configurada()
        return {"Authorization": f"APIKey {self._key}", "Content-Type": "application/json"}

    def consultar(self, numero: NumeroCNJ) -> list[ProcessoExterno]:
        """Instancias do processo encontradas no DataJud (lista vazia = nao encontrado).

        Guarda o resultado por 5 minutos: abrir o mesmo processo varias vezes nao repete a consulta.
        """
        indice = numero.indice_datajud()
        corpo = {"query": {"match": {"numeroProcesso": numero.digitos}}, "size": 5}
        bruto = self._chamar_com_cache(
            f"datajud:{indice}:{numero.digitos}", 5 * MINUTO, "POST", f"/api_publica_{indice}/_search", json=corpo
        )
        try:
            hits = bruto["hits"]["hits"]
        except (KeyError, TypeError) as exc:
            raise IntegracaoErro(self.servico, "Resposta inesperada do DataJud.") from exc
        return [self._mapear(h.get("_source", {})) for h in hits if isinstance(h, dict)]

    # ---------------------------------------------------------------- mapa

    def _mapear(self, fonte: dict) -> ProcessoExterno:
        movimentos = [self._movimento(m) for m in (fonte.get("movimentos") or []) if isinstance(m, dict)]
        movimentos.sort(key=lambda m: m.data or datetime.min, reverse=True)
        return ProcessoExterno(
            numero=str(fonte.get("numeroProcesso", "")),
            tribunal=str(fonte.get("tribunal", "")),
            grau=str(fonte.get("grau", "")),
            classe=str((fonte.get("classe") or {}).get("nome", "")),
            assuntos=tuple(str(a.get("nome", "")) for a in (fonte.get("assuntos") or []) if isinstance(a, dict)),
            orgao_julgador=str((fonte.get("orgaoJulgador") or {}).get("nome", "")),
            data_ajuizamento=_data(fonte.get("dataAjuizamento")),
            movimentos=tuple(movimentos[: self.MAX_MOVIMENTOS]),
        )

    @staticmethod
    def _movimento(m: dict) -> Movimento:
        complementos = [str(c.get("nome") or c.get("descricao") or "") for c in (m.get("complementosTabelados") or []) if isinstance(c, dict)]
        return Movimento(data=_data(m.get("dataHora")), nome=str(m.get("nome", "")), complemento="; ".join(c for c in complementos if c))


def _data(valor) -> datetime | None:
    """O DataJud mistura 'aaaa-mm-ddThh:mm:ss.000Z' e 'aaaammddhhmmss'."""
    if not valor:
        return None
    texto = str(valor)
    for formato in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(texto, formato)
        except ValueError:
            continue
    return None
