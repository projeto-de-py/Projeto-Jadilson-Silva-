"""Banco Central do Brasil: Sistema Gerenciador de Series Temporais (SGS).

API publica e gratuita, sem chave:
    https://api.bcb.gov.br/dados/serie/bcdata.sgs.<CODIGO>/dados?formato=json&dataInicial=dd/MM/aaaa&dataFinal=dd/MM/aaaa

Uso no escritorio: comparar a taxa de juros de um contrato com a TAXA MEDIA DE MERCADO
do mes da contratacao (base das acoes revisionais).

Como adicionar uma serie nova
-----------------------------
1. Confirme o codigo e o nome no catalogo oficial (https://dadosabertos.bcb.gov.br).
2. Acrescente uma `SerieBCB` em `SERIES` abaixo. So entram series CONFERIDAS: o codigo
   errado devolveria a taxa de OUTRA modalidade, e isso vira argumento juridico.
"""

from dataclasses import dataclass
from datetime import date

import httpx

from app.integrations.base import ClienteHttp
from app.integrations.cache import CacheTTL
from app.integrations.erros import DadosInvalidosError, IntegracaoErro

HORA = 3600


@dataclass(frozen=True)
class SerieBCB:
    """Metadados de uma serie do SGS que o sistema sabe consultar."""

    codigo: int
    slug: str  # nome curto usado nas rotas da nossa API
    nome: str
    unidade: str  # "% a.m."
    periodicidade: str  # "mensal"


@dataclass(frozen=True)
class PontoSerie:
    """Um valor da serie. Em series mensais `data` e o primeiro dia do mes de referencia."""

    data: date
    valor: float


# Series conferidas no catalogo do Banco Central (taxa media mensal de juros, % ao mes).
SERIES: dict[str, SerieBCB] = {
    s.slug: s
    for s in (
        SerieBCB(25435, "pf-total", "Pessoas físicas - total (todas as operações de crédito)", "% a.m.", "mensal"),
        SerieBCB(25462, "pf-recursos-livres", "Pessoas físicas - recursos livres - total", "% a.m.", "mensal"),
        SerieBCB(25470, "credito-pessoal-total", "Pessoas físicas - crédito pessoal total", "% a.m.", "mensal"),
        SerieBCB(25464, "credito-pessoal-nao-consignado", "Pessoas físicas - crédito pessoal não consignado", "% a.m.", "mensal"),
        SerieBCB(25469, "credito-pessoal-consignado", "Pessoas físicas - crédito pessoal consignado total", "% a.m.", "mensal"),
        SerieBCB(25466, "consignado-setor-privado", "Pessoas físicas - consignado para trabalhadores do setor privado", "% a.m.", "mensal"),
        SerieBCB(29976, "pessoal-nao-consignado-garantia-real", "Pessoas físicas - crédito pessoal não consignado com garantia real", "% a.m.", "mensal"),
        SerieBCB(25473, "aquisicao-de-bens-total", "Pessoas físicas - aquisição de bens total", "% a.m.", "mensal"),
        SerieBCB(25472, "aquisicao-de-outros-bens", "Pessoas físicas - aquisição de outros bens", "% a.m.", "mensal"),
    )
}


def serie_por_slug(slug: str) -> SerieBCB:
    try:
        return SERIES[slug]
    except KeyError:
        raise DadosInvalidosError("Banco Central", f"Série desconhecida: {slug}. Veja as disponíveis em /api/consultas/juros/series.") from None


class BancoCentralClient(ClienteHttp):
    """Cliente do SGS do Banco Central."""

    servico = "Banco Central"

    def __init__(
        self,
        base_url: str = "https://api.bcb.gov.br/dados/serie",
        *,
        http: httpx.Client | None = None,
        timeout: float = 20.0,
        cache: CacheTTL | None = None,
    ) -> None:
        super().__init__(base_url, http=http, timeout=timeout, cache=cache)

    def serie(self, codigo: int, inicio: date, fim: date) -> list[PontoSerie]:
        """Valores da serie entre `inicio` e `fim` (guardados por 6 horas)."""
        if inicio > fim:
            raise DadosInvalidosError(self.servico, "A data inicial não pode ser depois da final.")
        params = {"formato": "json", "dataInicial": _br(inicio), "dataFinal": _br(fim)}
        chave = f"sgs:{codigo}:{params['dataInicial']}:{params['dataFinal']}"
        bruto = self._chamar_com_cache(chave, 6 * HORA, "GET", f"/bcdata.sgs.{codigo}/dados", params=params)
        if not isinstance(bruto, list):
            raise IntegracaoErro(self.servico, "Resposta inesperada do Banco Central.")
        return [PontoSerie(data=_de_br(p["data"]), valor=float(p["valor"])) for p in bruto if p.get("valor") not in (None, "")]

    def taxa_do_mes(self, slug: str, ano: int, mes: int) -> PontoSerie | None:
        """Taxa media da serie no mes (ou None se o BC ainda nao divulgou aquele mes)."""
        serie = serie_por_slug(slug)
        if not (1 <= mes <= 12 and 1990 <= ano <= 2199):
            raise DadosInvalidosError(self.servico, "Informe um mês (1 a 12) e um ano válidos.")
        inicio = date(ano, mes, 1)
        fim = date(ano + (mes == 12), (mes % 12) + 1, 1)
        pontos = self.serie(serie.codigo, inicio, fim)
        do_mes = [p for p in pontos if (p.data.year, p.data.month) == (ano, mes)]
        return do_mes[0] if do_mes else None


def _br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def _de_br(texto: str) -> date:
    dia, mes, ano = texto.split("/")
    return date(int(ano), int(mes), int(dia))
