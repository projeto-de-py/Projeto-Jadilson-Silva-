"""Controle da IA do produto.

Tudo que define o comportamento da IA fica nesta pasta:

- ``perfis/``     quem a IA "e" (redator juridico + especialista da area), em .md
- ``tarefas/``    a instrucao de cada acao (resumir, contestar, revisar...), em .md
- ``guardrails/`` filtros de entrada (ofensas, injecao de prompt, dados pessoais)
                  e de saida (HTML seguro, citacoes a conferir)
- ``revisor.py``  revisao deterministica (digitacao, gramatica, tom, requisitos da peca)
- ``provedores.py`` unica porta para o modelo de IA (hoje: simulado)
- ``servico.py``  o fluxo completo de uma solicitacao
- ``schemas.py``  formatos de entrada e saida (Pydantic)
"""
