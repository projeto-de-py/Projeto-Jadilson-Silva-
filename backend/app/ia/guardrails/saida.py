"""Guardrails de SAIDA: nada da IA chega ao advogado sem passar por aqui.

- HTML so com tags permitidas e sem atributos (o front insere esse HTML no
  documento e o exibe em um cartao: nao pode carregar script nem link).
- Citacoes de jurisprudencia/sumula sao marcadas para conferir a fonte: a IA
  pode errar numero e tese, e peca com citacao falsa e responsabilidade do advogado.
- Tamanho e quantidade limitados.
"""

import re
from html import escape
from html.parser import HTMLParser

from app.ia.schemas import Sugestao

TAGS_PERMITIDAS = {"p", "h2", "h3", "ol", "ul", "li", "strong", "em", "br", "blockquote"}
_VAZIAS = {"br"}
_DESCARTAR_CONTEUDO = {"script", "style", "iframe", "object", "embed", "template"}
MAX_SUGESTOES = 8


class _Saneador(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.saida: list[str] = []
        self._abertas: list[str] = []
        self._ignorar = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in _DESCARTAR_CONTEUDO:
            self._ignorar += 1
            return
        if self._ignorar or tag not in TAGS_PERMITIDAS:
            return
        self.saida.append(f"<{tag}>")
        if tag not in _VAZIAS:
            self._abertas.append(tag)

    def handle_startendtag(self, tag: str, attrs) -> None:
        if not self._ignorar and tag == "br":
            self.saida.append("<br>")

    def handle_endtag(self, tag: str) -> None:
        if tag in _DESCARTAR_CONTEUDO:
            self._ignorar = max(0, self._ignorar - 1)
            return
        if self._ignorar or tag not in TAGS_PERMITIDAS or tag in _VAZIAS:
            return
        if tag in self._abertas:
            while self._abertas:
                aberta = self._abertas.pop()
                self.saida.append(f"</{aberta}>")
                if aberta == tag:
                    break

    def handle_data(self, data: str) -> None:
        if not self._ignorar:
            self.saida.append(escape(data, quote=False))

    def resultado(self) -> str:
        while self._abertas:
            self.saida.append(f"</{self._abertas.pop()}>")
        return "".join(self.saida)


def sanitizar_html(html: str) -> str:
    s = _Saneador()
    s.feed(html)
    s.close()
    return s.resultado()


_CITACAO = re.compile(
    r"(s[uú]mula\s+(vinculante\s+)?n?[ºo.]?\s*\d+|\bresp\b|\bagrg\b|\bhc\s+\d|\badi\s+\d|\badpf\s+\d|"
    r"\btema\s+\d+|\bre\s+\d{3,}|\bstj\b|\bstf\b|\btst\b|orienta[cç][aã]o jurisprudencial|\boj\s+n?[ºo.]?\s*\d+)",
    re.IGNORECASE,
)


def cita_jurisprudencia(texto: str) -> bool:
    return bool(_CITACAO.search(texto))


def validar_sugestoes(sugestoes: list[Sugestao]) -> tuple[list[Sugestao], list[str]]:
    """Saneia o HTML, marca citacoes e limita a quantidade. Devolve (lista, avisos)."""
    avisos: list[str] = []
    resultado: list[Sugestao] = []
    for s in sugestoes[:MAX_SUGESTOES]:
        html = sanitizar_html(s.html)
        precisa_conferir = cita_jurisprudencia(html) or cita_jurisprudencia(s.previa)
        if precisa_conferir and "CONFIRA A FONTE" not in html:
            html += "<p><em>[CONFIRA A FONTE]</em></p>"
        resultado.append(s.model_copy(update={"html": html, "verificar_fonte": precisa_conferir}))
    if any(s.verificar_fonte for s in resultado):
        avisos.append(
            "Há sugestões que citam súmula, tema ou julgado. Confira número e tese na fonte oficial antes de usar."
        )
    if len(sugestoes) > MAX_SUGESTOES:
        avisos.append(f"Foram mostradas as {MAX_SUGESTOES} primeiras sugestões.")
    return resultado, avisos
