"""Unica porta entre o sistema e o modelo de IA.

Nada fora deste arquivo conversa com um provedor externo. Hoje existe apenas o
provedor SIMULADO (offline, deterministico): ele devolve o mesmo formato JSON
que um modelo real devolveria, entao todo o fluxo (validacao, guardrails,
auditoria, front-end) ja funciona ponta a ponta.

Provedores: `simulado` (padrao, offline) e `openrouter` (modelo Google
gratuito via OpenRouter, exige OPENROUTER_API_KEY). Para outro modelo, implemente `Provedor.gerar` e registre
em `obter_provedor`. O restante do sistema nao muda.
"""

import json
import re
import time
from dataclasses import dataclass, field
from typing import Protocol

import httpx

from app.config import get_settings
from app.ia.schemas import AreaIA


@dataclass
class PedidoProvedor:
    tarefa: str
    sistema: str  # perfis (redator + area) - usado por provedores reais
    usuario: str  # instrucao da tarefa + pedido - usado por provedores reais
    area: AreaIA | None = None
    # Dados estruturados ja mascarados (PII) - usados pelo provedor simulado.
    contexto: dict = field(default_factory=dict)


class Provedor(Protocol):
    nome: str
    simulado: bool

    def gerar(self, pedido: PedidoProvedor) -> str:
        """Devolve JSON (tarefas de sugestao) ou texto puro (autocompletar)."""


class ProvedorIndisponivelError(Exception):
    """Provedor nao configurado ou fora do ar (vira 503 na API)."""


# --------------------------------------------------------------- simulado

def _p(texto: str) -> str:
    return f"<p>{texto}</p>"


def _resumo(caso: dict | None, contexto_texto: str = "") -> dict:
    if not caso and contexto_texto.strip():
        # Processo informado como texto (ainda nao esta no banco): resume o que foi enviado.
        linhas = [f"<p>{l.strip()}</p>" for l in contexto_texto.splitlines() if l.strip()]
        return {"perguntas": [], "sugestoes": [{
            "titulo": "Resumo do processo",
            "previa": linhas[0][3:-4][:140],
            "html": "<h2>RESUMO DO PROCESSO</h2>" + "".join(linhas) + _p("<em>Rascunho gerado a partir dos dados informados. Confira antes de usar.</em>"),
            "tipo": "Resumo",
            "categoria": "conteudo",
            "motivo": "Montado so com os dados do processo vinculado.",
        }]}
    if not caso:
        return {"perguntas": ["Qual processo devo resumir? Vincule um caso ou envie os dados do processo."], "sugestoes": []}
    prazos = [p for p in caso.get("prazos", []) if not p.get("cumprido")]
    linhas = [
        "<h2>RESUMO DO PROCESSO</h2>",
        _p(f"<strong>Processo:</strong> {caso.get('numero_processo') or 'sem número'} — {caso.get('titulo') or ''}."),
        _p(f"<strong>Cliente:</strong> {caso.get('cliente', '[CLIENTE]')}."),
        _p(f"<strong>Área e tipo:</strong> {caso.get('area', '')} ({caso.get('tipo_demanda', '')})."),
        _p(f"<strong>Situação:</strong> {caso.get('status', '')}."),
    ]
    if caso.get("observacoes"):
        linhas.append(_p(f"<strong>Observações:</strong> {caso['observacoes']}"))
    if prazos:
        itens = "; ".join(f"{p['titulo']} ({p['data_limite']})" for p in prazos)
        linhas.append(_p(f"<strong>Prazos em aberto:</strong> {itens}."))
    else:
        linhas.append(_p("<strong>Prazos em aberto:</strong> nenhum registrado."))
    linhas.append(_p("<em>Rascunho gerado a partir dos dados cadastrados. Confira antes de usar.</em>"))
    return {
        "perguntas": [],
        "sugestoes": [{
            "titulo": "Resumo do processo",
            "previa": f"{caso.get('cliente', '')} · {caso.get('status', '')} · {len(prazos)} prazo(s) em aberto.",
            "html": "".join(linhas),
            "tipo": "Resumo",
            "categoria": "conteudo",
            "motivo": "Montado só com os dados do caso cadastrado.",
        }],
    }


def _contestacao(caso: dict | None, texto: str) -> dict:
    if not caso and len(texto.strip()) < 80:
        return {"perguntas": ["O que a parte contrária alegou? Vincule o caso ou cole o resumo dos fatos da inicial."], "sugestoes": []}
    cliente = (caso or {}).get("cliente", "[NOME DO CLIENTE]")
    fatos = (caso or {}).get("observacoes") or ""
    return {
        "perguntas": [],
        "sugestoes": [
            {
                "titulo": "Preliminares",
                "previa": "Inépcia, ilegitimidade, prescrição e impugnação do valor da causa, quando cabíveis.",
                "html": "<h2>II – DAS PRELIMINARES</h2>" + _p(f"[Examinar inépcia da inicial, ilegitimidade de parte e prescrição. Impugnar o valor da causa, se for o caso. Parte representada: {cliente}.]"),
                "tipo": "Trecho",
                "categoria": "juridico",
                "motivo": "Preliminares devem ser arguidas antes do mérito (art. 337 do CPC).",
            },
            {
                "titulo": "Mérito: impugnação específica",
                "previa": "Resposta ponto a ponto aos fatos da inicial (art. 341 do CPC).",
                "html": "<h2>III – DO MÉRITO</h2>" + _p("Impugna-se especificamente cada fato narrado na inicial, conforme o art. 341 do CPC, sob pena de presunção de veracidade.") + (_p(f"Contexto do caso: {fatos}") if fatos else "") + _p("[Detalhar a defesa com os documentos que a sustentam.]"),
                "tipo": "Trecho",
                "categoria": "juridico",
                "motivo": "A falta de impugnação específica gera presunção de veracidade.",
            },
        ],
    }


def _continuar(texto: str) -> dict:
    n = re.sub(r"\s+", " ", texto.lower())
    if "dos pedidos" not in n:
        return {"perguntas": [], "sugestoes": [{
            "titulo": "Seção de pedidos",
            "previa": "A peça ainda não tem a seção de pedidos.",
            "html": "<h2>DOS PEDIDOS</h2>" + _p("Ante o exposto, requer:") + "<ol><li><p>a citação da parte contrária para responder à ação;</p></li><li><p>a procedência dos pedidos formulados;</p></li><li><p>a condenação em custas e honorários advocatícios;</p></li><li><p>a produção de todos os meios de prova admitidos em direito.</p></li></ol>",
            "tipo": "Trecho",
            "categoria": "juridico",
            "motivo": "Os pedidos delimitam o que o juiz pode julgar.",
        }]}
    return {"perguntas": [], "sugestoes": [{
        "titulo": "Seção de provas",
        "previa": "Parágrafo sobre os meios de prova.",
        "html": "<h2>DAS PROVAS</h2>" + _p("Protesta-se pela produção de todos os meios de prova admitidos em direito, em especial a documental, o depoimento pessoal e a oitiva de testemunhas, se necessário."),
        "tipo": "Trecho",
        "categoria": "conteudo",
        "motivo": "A indicação das provas evita preclusão.",
    }]}


_COMPLETAR = [
    (r"(,\s*)?requer:?$", " a procedência total dos pedidos, com a condenação da parte ré ao pagamento das custas e dos honorários advocatícios."),
    (r"nestes termos,?$", " pede deferimento."),
    (r"respeitosamente,?$", " à presença de Vossa Excelência, apresentar o que segue."),
    (r"justi[cç]a gratuita$", ", nos termos do art. 98 do Código de Processo Civil."),
    (r"tutela de urg[eê]ncia$", ", presentes a probabilidade do direito e o perigo de dano, conforme o art. 300 do Código de Processo Civil."),
    (r"invers[aã]o do [oô]nus da prova$", ", nos termos do art. 6º, VIII, do Código de Defesa do Consumidor."),
    (r"taxa de juros$", " contratada, que supera a taxa média de mercado divulgada pelo Banco Central do Brasil para a modalidade,"),
    (r"d[aá]-se [aà] causa o valor de$", " R$ [VALOR DA CAUSA]."),
]


class ProvedorSimulado:
    nome = "simulado"
    simulado = True

    def gerar(self, pedido: PedidoProvedor) -> str:
        ctx = pedido.contexto
        texto = ctx.get("texto_documento", "")
        if pedido.tarefa == "completar":
            fim = ctx.get("texto_antes", "").rstrip().lower()
            for padrao, continuacao in _COMPLETAR:
                if re.search(padrao, fim):
                    return continuacao
            return ""
        if pedido.tarefa == "resumo":
            resposta = _resumo(ctx.get("caso"), ctx.get("contexto_processo", ""))
        elif pedido.tarefa == "contestacao":
            resposta = _contestacao(ctx.get("caso"), texto)
        elif pedido.tarefa == "continuar":
            resposta = _continuar(texto)
        elif pedido.tarefa == "livre":
            resposta = {"perguntas": [], "sugestoes": [{
                "titulo": "Pedido livre precisa da IA real",
                "previa": "O modo simulado não entende pedidos escritos livremente. Ligue o modelo de IA no servidor.",
                "html": _p("O modo simulado só atende os atalhos (resumir, contestação, revisar, continuar)."),
                "tipo": "Aviso",
                "categoria": "conteudo",
                "motivo": "Defina IA_PROVEDOR=openrouter e a OPENROUTER_API_KEY no .env do backend.",
            }]}
        else:  # revisar: a revisao objetiva e feita por app.ia.revisor no servico
            resposta = {"perguntas": [], "sugestoes": []}
        return json.dumps(resposta, ensure_ascii=False)


class ProvedorNaoConfigurado:
    """Provedor real ainda nao ligado: responde 503 em vez de fingir."""

    simulado = False

    def __init__(self, nome: str) -> None:
        self.nome = nome

    def gerar(self, pedido: PedidoProvedor) -> str:
        raise ProvedorIndisponivelError(
            f"O provedor de IA '{self.nome}' ainda não foi configurado neste servidor."
        )


# -------------------------------------------------------------- openrouter

class ProvedorOpenRouter:
    """Modelo de linguagem pelo OpenRouter (API compativel com a da OpenAI).

    Recebe so o que o servico ja filtrou: texto com CPF/CNPJ/e-mail/telefone
    mascarados (guardrails de entrada) e instrucoes de perfil + tarefa +
    exemplos. A chave vem do ambiente e nunca aparece em log ou resposta.
    """

    nome = "openrouter"
    simulado = False

    def __init__(
        self,
        api_key: str,
        modelo: str,
        url: str = "https://openrouter.ai/api/v1/chat/completions",
        timeout: int = 60,
        max_tokens: int = 2048,
        site_url: str = "",
        app_nome: str = "",
        alternativos: tuple[str, ...] = (),
        espera_retry: float = 2.0,
        http: httpx.Client | None = None,
    ) -> None:
        self._key = api_key
        self._alternativos = alternativos
        self._espera = espera_retry
        self._modelo = modelo
        self._url = url
        self._max_tokens = max_tokens
        self._site = site_url
        self._app = app_nome
        self._http = http or httpx.Client(timeout=timeout)

    def gerar(self, pedido: PedidoProvedor) -> str:
        corpo = {
            "model": self._modelo,
            "max_tokens": 300 if pedido.tarefa == "completar" else self._max_tokens,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": pedido.sistema},
                {"role": "user", "content": pedido.usuario},
            ],
        }
        headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}
        if self._site:
            headers["HTTP-Referer"] = self._site
        if self._app:
            headers["X-Title"] = self._app
        if pedido.tarefa == "completar":
            # Continuacao curta: sem "pensar" antes, senao os 300 tokens acabam no raciocinio e a resposta vem vazia.
            corpo["reasoning"] = {"enabled": False}
        if self._alternativos:
            # Reserva: se o modelo principal estiver saturado, o OpenRouter tenta os seguintes.
            corpo["models"] = [self._modelo, *self._alternativos]
        # Autocompletar e rapido e descartavel: sem nova tentativa. Pedidos do advogado tentam 2 vezes.
        tentativas = 1 if pedido.tarefa == "completar" else 2
        resposta = None
        for n in range(tentativas):
            try:
                resposta = self._http.post(self._url, headers=headers, json=corpo)
            except httpx.TimeoutException as exc:
                raise ProvedorIndisponivelError("A IA demorou demais para responder. Tente novamente.") from exc
            except httpx.HTTPError as exc:
                raise ProvedorIndisponivelError("Nao foi possivel falar com o provedor de IA.") from exc
            if resposta.status_code not in (429, 500, 502, 503) or n == tentativas - 1:
                break
            time.sleep(self._espera)  # modelo gratuito saturado: espera um pouco e tenta de novo

        if resposta.status_code in (401, 403):
            raise ProvedorIndisponivelError("O OpenRouter recusou a chave configurada neste servidor.")
        if resposta.status_code == 402:
            raise ProvedorIndisponivelError("A conta do OpenRouter esta sem creditos para este modelo.")
        if resposta.status_code == 404:
            raise ProvedorIndisponivelError("O modelo de IA configurado nao esta disponivel no OpenRouter agora.")
        if resposta.status_code == 429:
            raise ProvedorIndisponivelError(
                "O modelo gratuito do Google esta saturado agora (limite compartilhado). Tente de novo em instantes "
                "ou cadastre sua propria chave do Google AI Studio em openrouter.ai/settings/integrations para ter limite proprio."
            )
        if resposta.status_code >= 400:
            raise ProvedorIndisponivelError("O provedor de IA esta indisponivel no momento.")
        try:
            dados = resposta.json()
        except ValueError as exc:
            raise ProvedorIndisponivelError("Resposta invalida do provedor de IA.") from exc
        # O OpenRouter pode devolver HTTP 200 com {"error": {...}} (ex.: modelo gratuito saturado).
        if not isinstance(dados, dict) or dados.get("error"):
            raise ProvedorIndisponivelError("O modelo de IA nao conseguiu responder agora. Tente novamente.")
        try:
            texto = dados["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise ProvedorIndisponivelError("Resposta invalida do provedor de IA.") from exc
        if not str(texto).strip():
            raise ProvedorIndisponivelError("O provedor de IA devolveu uma resposta vazia.")
        return str(texto)


def obter_provedor(nome: str, http: httpx.Client | None = None) -> Provedor:
    """Escolhe o provedor pelo nome (`IA_PROVEDOR`/`LLM_PROVIDER`)."""
    if nome == "simulado":
        return ProvedorSimulado()
    if nome == "openrouter":
        cfg = get_settings()
        if not cfg.openrouter_api_key:
            return ProvedorNaoConfigurado(nome)  # sem chave: 503, nunca finge
        return ProvedorOpenRouter(
            api_key=cfg.openrouter_api_key.get_secret_value(),
            modelo=cfg.openrouter_model,
            url=cfg.openrouter_api_url,
            timeout=cfg.ia_timeout_segundos,
            max_tokens=cfg.ia_max_tokens,
            alternativos=tuple(m.strip() for m in cfg.openrouter_modelos_alternativos.split(",") if m.strip()),
            site_url=cfg.openrouter_site_url,
            app_nome=cfg.openrouter_app_nome,
            http=http,
        )
    return ProvedorNaoConfigurado(nome)
