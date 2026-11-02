"""Revisao deterministica de texto juridico (sem chamar nenhum modelo).

Serve a dois propositos:
- e o motor do provedor SIMULADO (a revisao ja funciona de verdade, offline);
- continua valendo quando o provedor real for ligado: as checagens objetivas
  (digitacao, requisitos da peca, tom) sao baratas, rapidas e nao alucinam.

Cada achado vira uma `Sugestao` com `categoria`, `severidade`, `trecho` e `motivo`.
"""

import re

from app.ia.guardrails.entrada import detectar_odio, normalizar, palavroes_encontrados, trechos_ofensivos
from app.ia.schemas import AreaIA, Sugestao


def _s(titulo, previa, html, *, categoria, severidade="info", tipo="Revisão", trecho=None, motivo=None) -> Sugestao:
    return Sugestao(
        titulo=titulo,
        previa=previa,
        html=html,
        tipo=tipo,
        categoria=categoria,
        severidade=severidade,
        trecho=trecho,
        motivo=motivo,
    )


def _contexto(texto: str, ini: int, fim: int, folga: int = 25) -> str:
    a = max(0, ini - folga)
    b = min(len(texto), fim + folga)
    return ("…" if a else "") + texto[a:b].strip() + ("…" if b < len(texto) else "")


# ------------------------------------------------------------------ digitacao

# Só espaço ou tab entre as palavras: quebra de linha separa títulos e parágrafos.
_REPETIDA = re.compile(r"\b([A-Za-zÀ-ÿ]{2,})[ \t]+\1\b", re.IGNORECASE)
_ESPACO_ANTES = re.compile(r"[ \t]+([,.;:!?])")
_SEM_ESPACO = re.compile(r"([,;])(?=[A-Za-zÀ-ÿ])")
_ESPACO_DUPLO = re.compile(r"(?<=\S)[ \t]{2,}(?=\S)")


def _digitacao(texto: str) -> list[Sugestao]:
    achados: list[Sugestao] = []
    for m in list(_REPETIDA.finditer(texto))[:3]:
        palavra = m.group(1)
        trecho = _contexto(texto, m.start(), m.end())
        corrigido = trecho.replace(m.group(0), palavra, 1)
        achados.append(_s(
            f"Palavra repetida: “{palavra}”",
            "A mesma palavra aparece duas vezes seguidas.",
            f"<p>{corrigido}</p>",
            categoria="digitacao",
            severidade="atencao",
            trecho=trecho,
            motivo="Repetição provavelmente acidental.",
        ))
    for regra, titulo, motivo in (
        (_ESPACO_ANTES, "Espaço antes da pontuação", "Em português não se deixa espaço antes de vírgula, ponto ou ponto e vírgula."),
        (_SEM_ESPACO, "Falta espaço depois da pontuação", "Vírgula e ponto e vírgula pedem um espaço depois."),
        (_ESPACO_DUPLO, "Espaços duplos", "Há mais de um espaço seguido entre palavras."),
    ):
        ocorrencias = list(regra.finditer(texto))
        if ocorrencias:
            primeira = ocorrencias[0]
            achados.append(_s(
                f"{titulo} ({len(ocorrencias)})",
                motivo,
                f"<p>{motivo}</p>",
                categoria="digitacao",
                severidade="info",
                trecho=_contexto(texto, primeira.start(), primeira.end()),
                motivo=motivo,
            ))
    return achados


# ------------------------------------------------------------------ gramatica

_GRAMATICA = [
    (r"\bhouveram\b", "houve", "“Haver” no sentido de “existir” é impessoal: usa-se “houve”."),
    (r"\bhaja visto\b", "haja vista", "A expressão correta é “haja vista”."),
    (r"\bafim de\b", "a fim de", "Locução de finalidade: “a fim de” (separado)."),
    (r"\bporisso\b", "por isso", "“Por isso” se escreve separado."),
    (r"\bmenas\b", "menos", "“Menos” é invariável."),
    (r"\ba n[ií]vel de\b", "em nível de / no âmbito de", "“A nível de” é construção desaconselhada; prefira “em nível de” ou “no âmbito de”."),
    (r"\bpra\b", "para", "Forma informal, inadequada em peça processual."),
    (r"\bvc\b|\bvcs\b|\btb\b|\bq\b", "forma completa", "Abreviação de conversa; use a forma completa."),
    (r"\bmeritissimo\b|\bmeritíssimo\b", "Excelentíssimo(a) Senhor(a) Doutor(a) Juiz(a)", "O tratamento adequado ao juiz é “Excelentíssimo(a) Senhor(a) Doutor(a) Juiz(a)”; “Meritíssimo” é uso antigo."),
]


def _gramatica(texto: str) -> list[Sugestao]:
    achados: list[Sugestao] = []
    for padrao, correto, motivo in _GRAMATICA:
        m = re.search(padrao, texto, re.IGNORECASE)
        if m:
            achados.append(_s(
                f"Revisar “{m.group(0)}”",
                f"Sugestão: {correto}.",
                f"<p>Use <strong>{correto}</strong>.</p>",
                categoria="gramatica",
                severidade="atencao",
                trecho=_contexto(texto, m.start(), m.end()),
                motivo=motivo,
            ))
    return achados


# --------------------------------------------------------------------- estilo

def _estilo(texto: str) -> list[Sugestao]:
    achados: list[Sugestao] = []
    for frase in re.split(r"(?<=[.!?])\s+", texto):
        palavras = frase.split()
        if len(palavras) > 70:
            achados.append(_s(
                f"Frase longa ({len(palavras)} palavras)",
                "Considere dividir em duas ou três frases para facilitar a leitura.",
                "<p>Divida a frase em orações menores, uma ideia por frase.</p>",
                categoria="estilo",
                trecho=" ".join(palavras[:14]) + "…",
                motivo="Frases acima de 70 palavras dificultam a leitura e a defesa oral.",
            ))
            if len(achados) == 3:
                break
    return achados


# ------------------------------------------------------------------------ tom

def _tom(texto: str) -> list[Sugestao]:
    achados: list[Sugestao] = []
    if detectar_odio(texto):
        achados.append(_s(
            "Trecho com possível discurso discriminatório ou ameaça",
            "O texto contém generalização degradante sobre um grupo ou ameaça. Remova ou reformule.",
            "<p>Reescreva com os fatos objetivos do caso, sem generalizar pessoas ou grupos.</p>",
            categoria="tom",
            severidade="critica",
            motivo="Discurso discriminatório e ameaças não cabem em peça processual e podem gerar responsabilização.",
        ))
    palavroes = palavroes_encontrados(texto)
    if palavroes:
        achados.append(_s(
            "Palavrões ou gírias de baixo calão",
            "O texto tem palavrões. Peça processual exige linguagem formal.",
            "<p>Substitua por termos formais e objetivos. Se for citação literal de prova, mantenha entre aspas e indique a fonte.</p>",
            categoria="tom",
            severidade="critica",
            trecho=", ".join(sorted(set(palavroes))),
            motivo="Palavrões não cabem em peça processual e podem prejudicar a credibilidade da tese e do advogado.",
        ))
    ofensas = trechos_ofensivos(texto)
    if ofensas:
        achados.append(_s(
            "Linguagem ofensiva",
            f"Termos como “{ofensas[0]}” enfraquecem a peça. Prefira fatos e fundamentos.",
            "<p>Substitua o adjetivo por fatos objetivos (o que foi feito, quando e com que prova).</p>",
            categoria="tom",
            severidade="atencao",
            trecho=", ".join(sorted(set(ofensas))),
            motivo=(
                "Peça processual deve ser respeitosa com a parte contrária e com o juízo. "
                "Se o termo for citação literal de prova, mantenha entre aspas e indique a fonte."
            ),
        ))
    return achados


# -------------------------------------------------------------------- juridico

def _tipo_da_peca(texto_norm: str, tipo_peca: str | None) -> str:
    base = normalizar(tipo_peca or "") + " " + texto_norm[:600]
    if "contestacao" in base:
        return "contestacao"
    if "recurso" in base or "apelacao" in base:
        return "recurso"
    if "procuracao" in base or "contrato de prestacao" in base:
        return "contrato"
    return "inicial"


def _juridico(texto: str, area: AreaIA | None, tipo_peca: str | None) -> list[Sugestao]:
    n = normalizar(texto)
    if len(n) < 200:
        return []  # texto curto demais para cobrar requisitos de uma peca
    tipo = _tipo_da_peca(n, tipo_peca)
    if tipo == "contrato":
        return []
    achados: list[Sugestao] = []

    def falta(*termos: str) -> bool:
        return not any(t in n for t in termos)

    if tipo in ("inicial", "contestacao") and falta("dos fatos", "dos fatos e"):
        achados.append(_s(
            "Seção de fatos ausente",
            "Não encontrei uma seção de fatos.",
            "<h2>I – DOS FATOS</h2><p>[Narrar os fatos em ordem cronológica, com datas e valores.]</p>",
            categoria="juridico",
            severidade="atencao",
            tipo="Trecho",
            motivo="Os pedidos precisam estar apoiados nos fatos narrados.",
        ))
    if tipo in ("inicial", "recurso") and falta("dos pedidos", "requer", "requer-se"):
        achados.append(_s(
            "Seção de pedidos ausente",
            "A peça não traz os pedidos (art. 319, IV, do CPC).",
            "<h2>DOS PEDIDOS</h2><p>Ante o exposto, requer:</p><ol><li><p>[Pedido principal];</p></li><li><p>a condenação em custas e honorários advocatícios;</p></li><li><p>a produção de todos os meios de prova admitidos em direito.</p></li></ol>",
            categoria="juridico",
            severidade="critica",
            tipo="Trecho",
            motivo="Sem pedidos, o juiz não tem o que julgar.",
        ))
    if tipo == "inicial" and falta("valor da causa", "da-se a causa", "da-se à causa", "atribui-se a causa"):
        achados.append(_s(
            "Valor da causa ausente",
            "Não encontrei a indicação do valor da causa (art. 319, V, do CPC).",
            "<p>Dá-se à causa o valor de R$ [VALOR DA CAUSA].</p>",
            categoria="juridico",
            severidade="critica",
            tipo="Trecho",
            motivo="O valor da causa é requisito da petição inicial.",
        ))
    if tipo == "inicial" and falta("gratuita"):
        achados.append(_s(
            "Justiça gratuita não requerida",
            "Se o cliente não puder arcar com as custas, o pedido deve constar da inicial.",
            "<h2>DA JUSTIÇA GRATUITA</h2><p>O(A) requerente declara não possuir condições de arcar com as custas e despesas do processo sem prejuízo do próprio sustento, requerendo os benefícios da justiça gratuita, nos termos do art. 98 do CPC.</p>",
            categoria="juridico",
            tipo="Trecho",
            motivo="Evita o recolhimento de custas e discussão posterior sobre o benefício.",
        ))
    if falta("pede deferimento", "termos em que", "p. deferimento"):
        achados.append(_s(
            "Fecho da peça",
            "Falta o fecho com local, data e assinatura.",
            "<p>Nestes termos,<br>pede deferimento.</p><p>Paulo Afonso/BA, [DATA].</p><p>[NOME DO ADVOGADO] — OAB/BA nº [NÚMERO]</p>",
            categoria="juridico",
            tipo="Trecho",
            motivo="O fecho identifica o advogado e a data da peça.",
        ))
    if tipo == "recurso" and falta("tempestiv"):
        achados.append(_s(
            "Tempestividade não demonstrada",
            "Recursos devem indicar que foram interpostos no prazo.",
            "<h2>DA TEMPESTIVIDADE</h2><p>A decisão foi publicada em [DATA]; o recurso é tempestivo, por interposto dentro do prazo legal de [Nº] dias.</p>",
            categoria="risco",
            severidade="atencao",
            tipo="Trecho",
            motivo="Recurso intempestivo não é conhecido.",
        ))
    if tipo == "contestacao" and area == AreaIA.TRABALHISTA and falta("prescri"):
        achados.append(_s(
            "Prescrição não analisada",
            "Na contestação trabalhista, avalie a prescrição bienal e quinquenal.",
            "<h2>DA PRESCRIÇÃO</h2><p>[Se cabível: arguir a prescrição bienal e a quinquenal, nos termos do art. 7º, XXIX, da Constituição Federal.]</p>",
            categoria="juridico",
            tipo="Trecho",
            motivo="A prescrição deve ser arguida na primeira oportunidade.",
        ))
    if tipo == "inicial" and area == AreaIA.BANCARIO and falta("banco central", "taxa media"):
        achados.append(_s(
            "Comparação com a taxa média de mercado",
            "Em ação revisional, a taxa contratada costuma ser comparada à taxa média do Banco Central.",
            "<p>A taxa de juros contratada, de [TAXA]% ao mês, supera a taxa média de mercado divulgada pelo Banco Central do Brasil para a modalidade na data da contratação, de [TAXA MÉDIA]% ao mês.</p>",
            categoria="juridico",
            tipo="Trecho",
            motivo="A diferença para a taxa média é o principal parâmetro de abusividade.",
        ))
    lacunas = len(re.findall(r"\[[^\]]{2,}\]", texto))
    if lacunas:
        achados.append(_s(
            f"{lacunas} campo(s) entre colchetes por preencher",
            "Ainda há lacunas do modelo no texto.",
            "<p>Preencha ou remova todos os campos [ENTRE COLCHETES] antes de protocolar.</p>",
            categoria="risco",
            severidade="atencao",
            tipo="Aviso",
            motivo="Peça protocolada com campos em branco pode ser indeferida ou gerar constrangimento.",
        ))
    return achados


_ORDEM_SEVERIDADE = {"critica": 0, "atencao": 1, "info": 2}


def analisar(texto: str, area: AreaIA | None = None, tipo_peca: str | None = None) -> list[Sugestao]:
    """Roda todas as checagens e devolve os achados, os mais graves primeiro."""
    if not texto.strip():
        return []
    achados = (
        _tom(texto)
        + _juridico(texto, area, tipo_peca)
        + _gramatica(texto)
        + _digitacao(texto)
        + _estilo(texto)
    )
    return sorted(achados, key=lambda s: _ORDEM_SEVERIDADE[s.severidade])
