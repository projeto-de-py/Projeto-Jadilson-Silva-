"""BrasilAPI (https://brasilapi.com.br): feriados nacionais, CEP e consulta de CNPJ.

Gratuita e sem chave. Usada para:
- feriados  -> calculadora de prazos (dias uteis);
- CEP       -> preencher endereco no cadastro de cliente;
- CNPJ      -> preencher razao social de cliente pessoa juridica.

O cliente devolve dataclasses simples; nao tem regra de negocio.
"""

from dataclasses import dataclass
from datetime import date

import httpx

from app.core.validacao import digitos, eh_cnpj
from app.integrations.base import ClienteHttp
from app.integrations.cache import CacheTTL
from app.integrations.erros import DadosInvalidosError, IntegracaoErro

DIA = 24 * 3600


@dataclass(frozen=True)
class Feriado:
    data: date
    nome: str
    tipo: str  # "national" na BrasilAPI


@dataclass(frozen=True)
class Endereco:
    cep: str
    estado: str
    cidade: str
    bairro: str
    rua: str


@dataclass(frozen=True)
class Empresa:
    cnpj: str
    razao_social: str
    nome_fantasia: str
    situacao: str
    municipio: str
    uf: str


class BrasilAPIClient(ClienteHttp):
    """Cliente da BrasilAPI. Cada metodo valida a entrada ANTES de chamar a internet."""

    servico = "BrasilAPI"

    def __init__(
        self,
        base_url: str = "https://brasilapi.com.br/api",
        *,
        http: httpx.Client | None = None,
        timeout: float = 15.0,
        cache: CacheTTL | None = None,
    ) -> None:
        super().__init__(base_url, http=http, timeout=timeout, cache=cache)

    def feriados(self, ano: int) -> list[Feriado]:
        """Feriados nacionais do ano (guardados por 30 dias: nao mudam)."""
        if not 1900 <= ano <= 2199:
            raise DadosInvalidosError(self.servico, "Informe um ano entre 1900 e 2199.")
        bruto = self._chamar_com_cache(f"feriados:{ano}", 30 * DIA, "GET", f"/feriados/v1/{ano}")
        return [Feriado(data=date.fromisoformat(i["date"]), nome=i["name"], tipo=i.get("type", "")) for i in _como_lista(bruto)]

    def cep(self, cep: str) -> Endereco:
        """Endereco de um CEP (guardado por 1 dia)."""
        limpo = digitos(cep)
        if len(limpo) != 8:
            raise DadosInvalidosError(self.servico, "O CEP precisa ter 8 dígitos.")
        d = self._chamar_com_cache(f"cep:{limpo}", DIA, "GET", f"/cep/v2/{limpo}")
        return Endereco(
            cep=limpo,
            estado=d.get("state", ""),
            cidade=d.get("city", ""),
            bairro=d.get("neighborhood", ""),
            rua=d.get("street", ""),
        )

    def cnpj(self, cnpj: str) -> Empresa:
        """Dados publicos de um CNPJ na Receita Federal (guardados por 1 dia)."""
        limpo = digitos(cnpj)
        if not eh_cnpj(limpo):
            raise DadosInvalidosError(self.servico, "CNPJ inválido: confira os 14 dígitos.")
        d = self._chamar_com_cache(f"cnpj:{limpo}", DIA, "GET", f"/cnpj/v1/{limpo}")
        return Empresa(
            cnpj=limpo,
            razao_social=d.get("razao_social", ""),
            nome_fantasia=d.get("nome_fantasia") or "",
            situacao=d.get("descricao_situacao_cadastral", ""),
            municipio=d.get("municipio", ""),
            uf=d.get("uf", ""),
        )


def _como_lista(bruto) -> list[dict]:
    """A BrasilAPI devolve uma lista de objetos; qualquer outra forma e resposta inesperada."""
    if not isinstance(bruto, list):
        raise IntegracaoErro(BrasilAPIClient.servico, "Resposta inesperada da BrasilAPI.")
    return [i for i in bruto if isinstance(i, dict)]
