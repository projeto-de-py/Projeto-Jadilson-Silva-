"""Comparacao da taxa de juros de um contrato com a taxa media de mercado (Banco Central).

E a base de uma acao revisional: "a taxa contratada foi X% ao mes; a media de mercado
naquele mes, para aquela modalidade, era Y% ao mes".

IMPORTANTE (limite juridico): o servico entrega NUMEROS e uma FAIXA descritiva. Ele nao
afirma que a taxa e "abusiva": isso e juizo do advogado, caso a caso, a partir da
jurisprudencia aplicavel.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.integrations.bcb import BancoCentralClient, SerieBCB, serie_por_slug
from app.integrations.erros import DadosInvalidosError, IntegracaoNaoEncontradaError

AVISO = (
    "Indicador numérico para apoiar a análise. A abusividade é avaliada caso a caso pelo "
    "juiz, conforme a jurisprudência; confira a fonte oficial do Banco Central."
)

# (limite superior da razao taxa_contrato / taxa_media, descricao da faixa)
_FAIXAS = (
    (Decimal("1.0"), "Igual ou abaixo da média de mercado"),
    (Decimal("1.5"), "Acima da média (até 1,5 vez)"),
    (Decimal("2.0"), "Entre 1,5 e 2 vezes a média"),
    (Decimal("3.0"), "Entre 2 e 3 vezes a média"),
)
_FAIXA_MAXIMA = "Mais de 3 vezes a média"


@dataclass(frozen=True)
class ComparacaoJuros:
    serie: SerieBCB
    mes_referencia: date
    taxa_contrato_mensal: Decimal
    taxa_media_mensal: Decimal
    diferenca_pontos: Decimal  # taxa_contrato - taxa_media (pontos percentuais ao mes)
    razao: Decimal  # taxa_contrato / taxa_media
    faixa: str
    acima_da_media: bool
    taxa_contrato_anual: Decimal  # equivalente composta: (1+i)^12 - 1
    taxa_media_anual: Decimal
    aviso: str = AVISO


class JurosService:
    def __init__(self, banco_central: BancoCentralClient):
        self.bc = banco_central

    def series_disponiveis(self) -> list[SerieBCB]:
        from app.integrations.bcb import SERIES

        return list(SERIES.values())

    def comparar(self, slug: str, data_contrato: date, taxa_contrato_mensal: Decimal) -> ComparacaoJuros:
        """Compara a taxa do contrato com a media do mes da contratacao."""
        if data_contrato > date.today():
            raise DadosInvalidosError(self.bc.servico, "A data do contrato não pode estar no futuro.")
        if taxa_contrato_mensal <= 0 or taxa_contrato_mensal > 100:
            raise DadosInvalidosError(self.bc.servico, "Informe a taxa mensal entre 0 e 100 (% ao mês).")
        serie = serie_por_slug(slug)

        ponto = self.bc.taxa_do_mes(slug, data_contrato.year, data_contrato.month)
        if ponto is None:
            raise IntegracaoNaoEncontradaError(
                self.bc.servico, "O Banco Central ainda não divulgou a taxa média deste mês para esta modalidade."
            )
        media = Decimal(str(ponto.valor))
        razao = (taxa_contrato_mensal / media).quantize(Decimal("0.01"))
        return ComparacaoJuros(
            serie=serie,
            mes_referencia=ponto.data,
            taxa_contrato_mensal=taxa_contrato_mensal,
            taxa_media_mensal=media,
            diferenca_pontos=(taxa_contrato_mensal - media).quantize(Decimal("0.01")),
            razao=razao,
            faixa=_faixa(taxa_contrato_mensal / media),
            acima_da_media=taxa_contrato_mensal > media,
            taxa_contrato_anual=_anual(taxa_contrato_mensal),
            taxa_media_anual=_anual(media),
        )


def _faixa(razao: Decimal) -> str:
    for limite, descricao in _FAIXAS:
        if razao <= limite:
            return descricao
    return _FAIXA_MAXIMA


def _anual(taxa_mensal_percentual: Decimal) -> Decimal:
    """Equivalente anual composto, em %: ((1 + i)^12 - 1) * 100."""
    i = taxa_mensal_percentual / Decimal(100)
    return (((1 + i) ** 12 - 1) * 100).quantize(Decimal("0.01"))
