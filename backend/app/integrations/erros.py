"""Erros das integracoes externas.

Hierarquia (tudo herda de IntegracaoErro, entao um unico `except` pega qualquer falha):

    IntegracaoErro                     falha generica ao falar com o servico externo
    ├── IntegracaoNaoConfiguradaError  falta chave/token neste servidor      -> HTTP 503
    ├── IntegracaoNaoEncontradaError   o servico respondeu "nao existe" (404) -> HTTP 404
    └── DadosInvalidosError            nossa entrada nao serve (ex.: CEP mal formado) -> HTTP 422

A mensagem (`mensagem`) e sempre SEGURA para mostrar ao usuario: nunca carrega token,
cabecalhos nem o corpo bruto da resposta do provedor.
"""


class IntegracaoErro(Exception):
    """Falha ao falar com um servico externo."""

    def __init__(self, servico: str, mensagem: str, status: int | None = None):
        super().__init__(mensagem)
        self.servico = servico
        self.mensagem = mensagem
        self.status = status


class IntegracaoNaoConfiguradaError(IntegracaoErro):
    """Chave ou token do servico nao foi definido neste servidor."""


class IntegracaoNaoEncontradaError(IntegracaoErro):
    """O servico externo respondeu que o recurso pedido nao existe."""


class DadosInvalidosError(IntegracaoErro):
    """A entrada recebida nao pode ser enviada ao servico (validacao local, sem chamar a API)."""

    def __init__(self, servico: str, mensagem: str):
        super().__init__(servico, mensagem, status=422)
