"""ClienteHttp: a classe-mae de todo cliente de API externa.

Para criar a integracao com uma API nova, herde desta classe:

    class MinhaApiClient(ClienteHttp):
        servico = "MinhaApi"                       # aparece nas mensagens de erro

        def __init__(self, token, http=None):
            super().__init__("https://api.exemplo.com/v1", http=http)
            self._token = token

        def _cabecalhos(self) -> dict:             # gancho: autenticacao desta API
            return {"Authorization": f"Bearer {self._token}"}

        def buscar(self, id_: str) -> dict:
            return self._chamar("GET", f"/itens/{id_}")

O que a base resolve para voce:
- tempo limite em toda chamada (nenhuma requisicao fica pendurada);
- erros de rede, 401/403, 404, 429 e 5xx viram IntegracaoErro com mensagem SEGURA;
- o cliente HTTP pode ser injetado (`http=`), o que torna os testes offline;
- cache opcional por chamada (`_chamar_com_cache`).
"""

import httpx

from app.integrations.cache import CacheTTL
from app.integrations.erros import (
    IntegracaoErro,
    IntegracaoNaoConfiguradaError,
    IntegracaoNaoEncontradaError,
)

JSON = dict | list


class ClienteHttp:
    """Cliente HTTP generico com tratamento de erro padronizado."""

    #: Nome humano do servico (usado nas mensagens de erro). Sobrescreva na subclasse.
    servico: str = "Servico externo"

    def __init__(
        self,
        base_url: str,
        *,
        http: httpx.Client | None = None,
        timeout: float = 15.0,
        cache: CacheTTL | None = None,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._http = http or httpx.Client(timeout=timeout)
        self._cache = cache if cache is not None else CacheTTL()

    # ------------------------------------------------------------ ganchos

    def _cabecalhos(self) -> dict:
        """Cabecalhos de autenticacao desta API. Subclasses sobrescrevem; pode levantar
        IntegracaoNaoConfiguradaError se faltar a chave."""
        return {}

    def _nao_configurada(self) -> IntegracaoNaoConfiguradaError:
        return IntegracaoNaoConfiguradaError(self.servico, f"O {self.servico} não está configurado neste servidor.")

    # ----------------------------------------------------------- chamadas

    def _chamar(
        self,
        metodo: str,
        caminho: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        url_completa: bool = False,
    ) -> JSON:
        """Faz a chamada e devolve o JSON. Qualquer falha vira IntegracaoErro segura."""
        url = caminho if url_completa else f"{self._base}{caminho}"
        cabecalhos = {"Accept": "application/json", **self._cabecalhos()}
        try:
            resposta = self._http.request(metodo, url, headers=cabecalhos, json=json, params=params)
        except httpx.TimeoutException as exc:
            raise IntegracaoErro(self.servico, f"{self.servico} demorou demais para responder.") from exc
        except httpx.HTTPError as exc:
            raise IntegracaoErro(self.servico, f"Não foi possível conectar ao {self.servico}.") from exc
        self._conferir_status(resposta)
        try:
            return resposta.json()
        except ValueError as exc:
            raise IntegracaoErro(self.servico, f"Resposta inválida do {self.servico}.", resposta.status_code) from exc

    def _chamar_com_cache(self, chave: str, ttl_segundos: float, metodo: str, caminho: str, **kw) -> JSON:
        """Igual a `_chamar`, mas repete a resposta guardada enquanto ela estiver valida."""
        guardado = self._cache.obter(chave)
        if guardado is not None:
            return guardado
        resultado = self._chamar(metodo, caminho, **kw)
        self._cache.guardar(chave, resultado, ttl_segundos)
        return resultado

    # ------------------------------------------------------------- erros

    def _conferir_status(self, resposta: httpx.Response) -> None:
        codigo = resposta.status_code
        if codigo < 400:
            return
        if codigo in (401, 403):
            raise IntegracaoErro(self.servico, f"O {self.servico} recusou as credenciais configuradas neste servidor.", codigo)
        if codigo == 404:
            raise IntegracaoNaoEncontradaError(self.servico, f"O {self.servico} não encontrou o registro pedido.", codigo)
        if codigo == 429:
            raise IntegracaoErro(self.servico, f"Limite de uso do {self.servico} atingido. Tente de novo em instantes.", codigo)
        detalhe = self._resumo_do_erro(resposta)
        raise IntegracaoErro(
            self.servico,
            f"O {self.servico} recusou o pedido" + (f": {detalhe}" if detalhe else "."),
            codigo,
        )

    @staticmethod
    def _resumo_do_erro(resposta: httpx.Response) -> str:
        """Extrai uma descricao curta do erro do provedor, sem devolver o corpo inteiro."""
        try:
            corpo = resposta.json()
        except ValueError:
            return ""
        candidatos: list = []
        if isinstance(corpo, dict):
            erros = corpo.get("errors")
            if isinstance(erros, list):
                candidatos += [e.get("description") for e in erros if isinstance(e, dict)]
            candidatos += [corpo.get("detail"), corpo.get("message"), corpo.get("error")]
        textos = [str(c) for c in candidatos if isinstance(c, str) and c]
        return "; ".join(textos)[:200]
