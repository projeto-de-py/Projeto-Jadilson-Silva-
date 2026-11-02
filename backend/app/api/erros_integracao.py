"""Traducao dos erros das integracoes para respostas HTTP (um unico lugar, para todas as rotas).

    IntegracaoNaoConfiguradaError -> 503  (falta chave neste servidor)
    DadosInvalidosError           -> 422  (a entrada nao serve)
    IntegracaoNaoEncontradaError  -> 404  (o servico externo nao tem o registro)
    limite de uso do provedor     -> 429
    qualquer outra falha          -> 502  (o servico externo falhou)
"""

from fastapi import HTTPException, status

from app.integrations.erros import (
    DadosInvalidosError,
    IntegracaoErro,
    IntegracaoNaoConfiguradaError,
    IntegracaoNaoEncontradaError,
)


def http_de_integracao(exc: IntegracaoErro) -> HTTPException:
    if isinstance(exc, IntegracaoNaoConfiguradaError):
        codigo = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(exc, DadosInvalidosError):
        codigo = status.HTTP_422_UNPROCESSABLE_CONTENT
    elif isinstance(exc, IntegracaoNaoEncontradaError):
        codigo = status.HTTP_404_NOT_FOUND
    elif exc.status == 429:
        codigo = status.HTTP_429_TOO_MANY_REQUESTS
    else:
        codigo = status.HTTP_502_BAD_GATEWAY
    return HTTPException(codigo, exc.mensagem)
