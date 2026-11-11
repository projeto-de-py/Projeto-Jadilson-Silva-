# Sobre o app: Sistema de Gestão de Casos e Agenda

**Advocacia Jadilson Silva · Paulo Afonso/BA**

Este documento explica, em linguagem direta, do que se trata o projeto, qual é a ideia central, como ele
funciona e o que já existe. Para detalhes técnicos de cada parte, veja o [README da raiz](../README.md),
o [README do backend](../backend/README.md) e o [CONTEXTO_IA.md](CONTEXTO_IA.md).

---

## 1. A ideia central

Um escritório de advocacia pequeno vive de **prazos, processos e peças escritas**. Perder um prazo é o
erro mais caro da profissão, e redigir peças consome a maior parte do dia.

O app junta, em um só lugar, o que o advogado usa todos os dias:

1. **Ver o que importa agora**: quais prazos vencem, quais processos andam, quem são os clientes.
2. **Escrever a peça sem sair do sistema**: um editor parecido com o Word, com modelos por área do direito.
3. **Ter uma IA como assistente, nunca como autora**: ela sugere, aponta erros e resume; **o advogado decide
   o que entra no documento** (Adicionar ou Ignorar).

Em uma frase: **uma mesa de trabalho jurídica com prazos em primeiro plano e um redator com IA ao lado.**

### Para quem é

Advogado(a) e equipe de um escritório que atua em **Direito Trabalhista, Bancário/Consumidor e Previdenciário**.
Há dois tipos de conta: *Advogado* e *Funcionário*, e o **advogado principal** (administrador) controla quem
vê o quê.

### Princípios do projeto

- **Prazo antes de tudo:** a tela inicial e a central de prazos destacam o que vence hoje e o que está perto de vencer.
- **Revisão humana sempre:** nenhuma sugestão de IA entra no texto sem o clique do advogado.
- **Segurança no servidor:** esconder um botão na tela não é controle de acesso; as permissões valem na API.
- **Honestidade com o conteúdo jurídico:** a IA não inventa lei, súmula ou número de processo. Onde não souber,
  deixa `[COLCHETES]` ou `[CONFIRA A FONTE]`.

---

## 2. Como o app funciona (visão geral)

```
 Navegador (React)  ──►  API (FastAPI)  ──►  Banco (MySQL)
   telas e editor          regras e segurança    dados do escritório
        │                        │
        │                        └──►  Módulo de IA (app/ia)
        └─ Editor de documentos          perfis, tarefas, filtros e auditoria
```

1. O advogado **entra** com e-mail e senha. A sessão fica em um cookie protegido (o JavaScript não consegue lê-lo).
2. Na **página inicial** vê os atalhos: prazos urgentes, processos e clientes.
3. Abre um **processo**, acompanha os andamentos e clica em **Editar documento**: o sistema abre (ou cria) a peça
   daquele processo, já com cliente e número preenchidos.
4. No **editor**, escreve, formata e exporta em PDF. A IA ajuda com sugestões que aparecem **dentro do texto**.
5. Prazos e audiências aparecem na **Agenda** e na **Central de Prazos**.

---

## 3. Funcionalidades

### 3.1 Tela inicial (acesso rápido)
- Atalhos com contagem: prazos vencidos ou para hoje, perto de vencer (até 3 dias), processos ativos e clientes.
- **Painel de processos:** cada processo com fase, data de abertura, próximo prazo e a situação desse prazo.
- Listas de **próximos prazos** e de **clientes**, com atalho para criar cliente e processo.

### 3.2 Processos
- Lista e **funil por etapa** (petição inicial, instrução, sentença, recursal, concluído).
- **Andamentos** em linha do tempo, **exportar PDF** do processo e **Editar documento**.
- Cadastro de novo processo.

### 3.3 Prazos
- Prazos agrupados por urgência, com a situação em palavras simples: **Vencido**, **Vence hoje**,
  **Perto de vencer** e **No prazo**.
- Marcar como **cumprido**, filtrar por área e buscar.
- **Calculadora de prazos:** conta dias úteis ou corridos a partir da intimação, ignora feriados nacionais e
  prorroga para o próximo dia útil.

### 3.4 Agenda (no estilo do Notion Calendar)
- Visões **Mês, Semana, Dia e Lista**, mini-calendário e botão "Hoje".
- Filtros por tipo (audiência, audiência virtual, reunião, conciliação, despacho).
- **Novo evento** e painel de detalhes do evento.

### 3.5 Documentos: o "Word da advocacia"
- **Modelos por área** (trabalhista, bancário, previdenciário e geral): reclamação, contestação, recurso ordinário,
  revisional, exibição de documentos, negativação indevida, aposentadoria, auxílio por incapacidade, BPC/LOAS,
  procuração e contrato de honorários.
- **Editor com faixa de formatação:** estilos, fonte, tamanho, negrito/itálico/sublinhado, cor, realce,
  alinhamento (inclusive justificado), entrelinhas, listas, citação longa e tabelas.
- **Página A4** com o padrão do escritório (margens 3/2/2/3 cm, Times New Roman 12, entrelinhas 1,5),
  painel com dados do processo e índice da peça, contagem de páginas e palavras, zoom.
- **Importar** .docx, .txt e .html, e **exportar PDF**. Salva sozinho.

### 3.6 IA no editor
- **Perguntar à IA:** caixa com atalhos (*Resumir este processo*, *Redigir contestação*, *Revisar o texto*,
  *Continuar a peça*) e estados de trabalho visíveis ("Entendendo o pedido", "Redigindo a sugestão"…).
- **Sugestões dentro do texto:** cartão abaixo do parágrafo, com motivo, trecho e botões **Adicionar** e **Ignorar**.
- **Autocompletar (texto fantasma):** ao parar de digitar, a IA propõe a continuação em cinza; **Tab** aceita,
  **Esc** descarta, **Ctrl + →** aceita uma palavra. Dá para desligar.
- **Revisão objetiva:** digitação, gramática, estilo, tom e requisitos da peça (pedidos, valor da causa, fecho,
  tempestividade, campos `[ ]` por preencher).
- **Filtros de segurança:** recusa pedidos com **palavrão, xingamento, discurso de ódio, ameaça** e tentativas de
  burlar as regras da IA; mascara CPF, CNPJ, e-mail e telefone; cita súmulas só marcando `[CONFIRA A FONTE]`.

### 3.6.1 Onde fica o controle da IA
Pasta [`backend/app/ia/`](../backend/app/ia/):

| Item | Função |
|---|---|
| `perfis/` | Quem a IA é: redator jurídico + especialista da área (arquivos `.md` editáveis) |
| `tarefas/` | Instrução de cada ação e formato obrigatório da resposta |
| `guardrails/` | Filtros de entrada (palavrão, ódio, injeção, dados pessoais) e de saída (HTML seguro, citações) |
| `revisor.py` | Revisão sem modelo |
| `provedores.py` | Única porta para o modelo de IA (hoje: simulado) |
| `servico.py` | Fluxo completo e auditoria |

### 3.7 Recursos gerais
- **Busca global (Ctrl/⌘ + K):** páginas, processos, prazos e clientes.
- **Tema escuro e claro**, paleta neutra, cantos *squircle*, ícones SF Symbols e espaçamento em escala 8/16/24.
- Clientes e Configurações do escritório.

### 3.8 Notificações
- O sino consulta notificações pessoais a cada 30 segundos, mostra a quantidade não lida e abre um painel dividido em Hoje e Anteriores.
- Cada item pode levar à tela relacionada e ser marcado como lido; também é possível marcar todas de uma vez.
- Prazos geram avisos nos marcos de 7, 3, 1 e 0 dias e enquanto estiverem vencidos. A geração ocorre na primeira leitura da API e é repetida com deduplicação; ainda não existe rotina cron.
- Criações de clientes, atribuições de casos, concessões/revogações de acesso e eventos financeiros também geram avisos sem incluir dados pessoais no texto.
- `notificacoes` guarda proprietário, tipo, severidade, texto curto, link interno, chave de deduplicação e data de leitura. O backend aplica o escopo de usuário em toda leitura e escrita.

Na implementação, `models/notificacao.py` define a tabela, `repositories/notificacao_repository.py` mantém todas as consultas por proprietário, `services/notificacao_service.py` aplica deduplicação e gera avisos de prazo/ações, e `api/routes/notificacoes.py` publica os endpoints autenticados. A migração `0012_notificacoes.py` cria o armazenamento depois da migração local de agenda `0011`. No navegador, `hooks/useNotificacoes.js` atualiza lista/contador por polling e dispara toast para itens novos; `components/layout/PainelNotificacoes.jsx`, usado pelo `Topbar`, mostra o badge e o dropdown.

---

## 4. Segurança

- Senhas com hash forte; sessão por **cookie HttpOnly** com **token CSRF** em toda escrita.
- **Limite de tentativas** de login e **revogação** da sessão no logout.
- **Permissões por caso** decididas no servidor; caso fora do escopo responde 404.
- IA: limite de uso por usuário, auditoria só com metadados (nunca o texto), HTML saneado e dados pessoais mascarados.
- Em produção a API recusa iniciar com configuração fraca.

---

## 5. Tecnologia

| Camada | Tecnologia |
|---|---|
| Frontend | React, Vite, Tailwind CSS, Radix UI, TipTap (editor), Motion, Recharts, ícones SF (`symbols-react`) |
| Backend | Python, FastAPI, Uvicorn, Pydantic, SQLAlchemy, Alembic |
| Banco | MySQL (SQLite para desenvolvimento e testes) |
| Testes | Pytest (mais de 250 testes no backend) |

---

## 6. Estado atual (o que é real e o que ainda é demonstração)

| Parte | Estado |
|---|---|
| Login, sessão, usuários, permissões | **Funcionando** com a API e o banco |
| API de clientes, casos, prazos e histórico | **Pronta no backend**, ainda **não ligada** às telas |
| Telas de Início, Processos, Prazos, Agenda, Clientes | **Dados de demonstração** no navegador |
| Documentos | Salvos **no navegador** (localStorage); falta guardar no banco |
| IA: caixa, sugestões, revisão e filtros | **Funcionando** com provedor **simulado** (sem modelo real) |
| IA com modelo real | **Pronta no backend** (OpenRouter com modelo gratuito do Google, exige `OPENROUTER_API_KEY`); falta colar a chave e avaliar por área |
| Notificações | **Ligadas ao backend** com deduplicação por usuário, avisos de prazo sob demanda, polling e toast no navegador |
| Assinatura eletrônica (ZapSign) e cobrança (Asaas) | **Pronto no backend** com webhooks seguros e testes simulados; falta ligar as telas e testar com as contas reais (sandbox) |
| Integrações (DataJud, Banco Central) | **Planejadas**, ainda não iniciadas |

## 7. Próximos passos

1. Ligar as telas à API de casos, clientes e prazos (trocar os dados de demonstração).
2. Guardar os documentos no banco, com versões e controle de edição simultânea.
3. Ligar o modelo de IA real e rodar a avaliação por área.
4. Perfil do usuário e convite de colaboradores.
5. Integrações: Banco Central e BrasilAPI (taxas, feriados), DataJud (andamentos), assinatura eletrônica.

> **Aviso:** a IA é uma ferramenta de apoio. Toda peça deve ser revisada e assumida pelo advogado responsável.
