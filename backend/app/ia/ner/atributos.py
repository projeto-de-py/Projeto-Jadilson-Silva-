"""Atributos (features) de cada palavra para o reconhecedor de entidades.

Há três conjuntos, do mais simples ao mais completo. O script de treino compara os três:

  palavra   só a própria palavra em minúsculas
  contexto  + as duas palavras de cada lado
  completo  + prefixo, sufixo, formato (maiúscula, número, pontuação) e pares de palavras
"""

import re

CONJUNTOS = ("palavra", "contexto", "completo")
_ROMANO = re.compile(r"^[ivxlcdm]+$", re.I)
_JANELA = (-2, -1, 1, 2)


def _formato(palavra: str) -> str:
    """'d' número, 'dx' mistura com número, 'AA' sigla, 'Aa' inicial maiúscula, 'x' minúscula, 'p' pontuação."""
    if palavra.isdigit():
        return "d"
    if any(c.isdigit() for c in palavra):
        return "dx"
    if palavra.isupper() and len(palavra) > 1:
        return "AA"
    if palavra[:1].isupper():
        return "Aa"
    return "x" if palavra.isalpha() else "p"


def _vizinha(palavras: list[str], posicao: int) -> str:
    if posicao < 0:
        return "<ini>"
    if posicao >= len(palavras):
        return "<fim>"
    return palavras[posicao].lower()


def atributos_do_token(palavras: list[str], i: int, conjunto: str = "completo") -> dict[str, int]:
    palavra = palavras[i]
    baixa = palavra.lower()
    atributos = {"w=" + baixa: 1, "bias": 1}
    if conjunto == "palavra":
        return atributos

    for deslocamento in _JANELA:
        atributos[f"w{deslocamento}=" + _vizinha(palavras, i + deslocamento)] = 1
    if conjunto == "contexto":
        return atributos

    atributos["fmt=" + _formato(palavra)] = 1
    atributos["romano"] = int(bool(_ROMANO.match(palavra)))
    atributos["tam>3"] = int(len(palavra) > 3)
    for n in (2, 3):
        if len(baixa) >= n:
            atributos[f"suf{n}=" + baixa[-n:]] = 1
            atributos[f"pre{n}=" + baixa[:n]] = 1
    for deslocamento in (-1, 1):
        vizinha = i + deslocamento
        if 0 <= vizinha < len(palavras):
            atributos[f"fmt{deslocamento}=" + _formato(palavras[vizinha])] = 1
    atributos[f"w-1w={_vizinha(palavras, i - 1)}|{baixa}"] = 1
    atributos[f"w+1w={baixa}|{_vizinha(palavras, i + 1)}"] = 1
    return atributos


def atributos_da_frase(palavras: list[str], conjunto: str = "completo") -> list[dict[str, int]]:
    return [atributos_do_token(palavras, i, conjunto) for i in range(len(palavras))]
