"""Camada de integracoes: tudo que conversa com APIs de terceiros.

Como esta pasta se organiza (leia antes de mexer):

    base.py       ClienteHttp  -> classe-mae de TODO cliente de API externa
                                  (timeout, erros padronizados, cache, injecao de HTTP)
    erros.py      IntegracaoErro e filhas -> o unico vocabulario de erro das integracoes
    cache.py      CacheTTL     -> cache em memoria com validade (nao repete chamada igual)

    brasilapi.py  BrasilAPIClient   -> feriados, CEP, CNPJ        (gratuita, sem chave)
    bcb.py        BancoCentralClient-> series SGS: taxas de juros (gratuita, sem chave)
    datajud.py    DataJudClient     -> andamentos de processos    (gratuita, chave publica do CNJ)

    (ZapSign, Asaas e o provedor de IA tambem seguem este padrao:
     ver app/services/zapsign.py, app/services/asaas.py e app/ia/provedores.py)

Regras de ouro:
1. Um CLIENTE so sabe falar HTTP com UMA API e devolve dados ja tipados (dataclasses).
   Nao tem regra de negocio, nao conhece rotas nem banco.
2. Um SERVICO (app/services) combina clientes + regras do escritorio.
3. Uma ROTA (app/api/routes) so valida entrada, chama o servico e traduz erros em HTTP.
4. O cliente HTTP e INJETAVEL (`http=`): nos testes entra um MockTransport e nenhum
   teste toca a internet.
"""
