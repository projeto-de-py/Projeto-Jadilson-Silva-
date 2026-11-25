"""Divide um texto em palavras, guardando a posição de cada uma no texto original.

Segue o jeito do LeNER-Br: datas e números de processo ficam em UM token
("14/11/2017", "1.0024.13.385589-0/001") e a pontuação sai separada ("art", ".", "178").
Treino e uso precisam tokenizar igual, por isso este é o único lugar que sabe como.
"""

import re
from dataclasses import dataclass

_TOKEN = re.compile(r"\w+(?:[./\-]\w+)*|[^\w\s]", re.UNICODE)


@dataclass(frozen=True)
class Token:
    texto: str
    inicio: int
    fim: int  # exclusivo


def tokenizar(texto: str) -> list[Token]:
    return [Token(m.group(0), m.start(), m.end()) for m in _TOKEN.finditer(texto)]
