"""Pseudonimizacao reversivel (cofre local) para proteger dados pessoais na IA.

Em vez de apagar os dados com um `[NOME]` generico (o que confunde o modelo externo e o faz
perguntar o nome do cliente de volta), cada dado recebe um identificador numerado consistente
dentro da mesma requisicao:

    "Carlos Silva"    -> "[PESSOA_1]"
    "Maria Souza"     -> "[PESSOA_2]"
    "123.456.789-09"  -> "[CPF_1]"

O mapa fica apenas em memoria durante a requisicao:
1. Antes de sair para o OpenRouter, `proteger()` troca os dados reais pelos marcadores.
2. O modelo redige a peca reutilizando `[PESSOA_1]`, `[CPF_1]`, etc.
3. Na volta, `restaurar()` devolve os dados reais ao advogado antes de exibir a resposta.
"""

from html import escape
import re

from app.ia.guardrails.entrada import _CNPJ, _CPF, _EMAIL, _FONE
from app.ia.ner.reconhecedor import LIMITE_MEDIA

_MARCADOR = re.compile(r"\[(?:PESSOA|CPF|CNPJ|EMAIL|TELEFONE)_\d+\]")

_PADROES_PII: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("CNPJ", _CNPJ),
    ("CPF", _CPF),
    ("EMAIL", _EMAIL),
    ("TELEFONE", _FONE),
)


class CofreAnonimizacao:
    """Mantem o mapa local `marcador <-> dado real` durante uma chamada a IA."""

    def __init__(self) -> None:
        self._por_marcador: dict[str, str] = {}
        self._por_chave: dict[tuple[str, str], str] = {}
        self._contadores: dict[str, int] = {}

    @property
    def mapa(self) -> dict[str, str]:
        return dict(self._por_marcador)

    def _registrar(self, tipo: str, original: str) -> str:
        valor = original.strip()
        chave = (tipo, valor.lower())
        if chave in self._por_chave:
            return self._por_chave[chave]
        proximo = self._contadores.get(tipo, 0) + 1
        self._contadores[tipo] = proximo
        marcador = f"[{tipo}_{proximo}]"
        self._por_chave[chave] = marcador
        self._por_marcador[marcador] = valor
        return marcador

    def registrar_pessoa(self, nome: str | None) -> str:
        """Registra um nome conhecido (ex.: cliente do caso) e devolve seu marcador."""
        if not nome or not nome.strip():
            return ""
        return self._registrar("PESSOA", nome)

    def _substituir_pessoas_conhecidas(self, texto: str) -> str:
        """Garante que nomes ja registrados no cofre sejam mascarados mesmo fora de contexto NER."""
        nomes = [
            (valor, marcador)
            for marcador, valor in self._por_marcador.items()
            if marcador.startswith("[PESSOA_") and len(valor) >= 3
        ]
        for valor, marcador in sorted(nomes, key=lambda par: len(par[0]), reverse=True):
            padrao = re.compile(rf"(?<!\w){re.escape(valor)}(?!\w)", re.IGNORECASE)
            texto = padrao.sub(marcador, texto)
        return texto

    def proteger(self, texto: str, *, ner=None, mascarar_nomes: bool = False, confianca_minima: float = LIMITE_MEDIA) -> str:
        """Troca PII (regex) e nomes (NER + cofre) por marcadores reversiveis."""
        if not texto:
            return texto

        for tipo, padrao in _PADROES_PII:
            texto = padrao.sub(lambda m, t=tipo: self._registrar(t, m.group(0)), texto)

        if mascarar_nomes:
            texto = self._substituir_pessoas_conhecidas(texto)
            if ner is not None:
                pessoas = [
                    e
                    for e in ner.extrair(texto)
                    if e.tipo == "PESSOA" and e.confianca >= confianca_minima and not _MARCADOR.search(e.texto)
                ]
                for pessoa in reversed(pessoas):
                    marcador = self._registrar("PESSOA", pessoa.texto)
                    texto = texto[: pessoa.inicio] + marcador + texto[pessoa.fim :]

        return texto

    def restaurar(self, texto: str, *, escapar_html: bool = False) -> str:
        """Recoloca os dados reais no texto devolvido pelo modelo externo."""
        if not texto or not self._por_marcador:
            return texto

        def _trocar(match: re.Match[str]) -> str:
            marcador = match.group(0)
            original = self._por_marcador.get(marcador)
            if original is None:
                return marcador
            return escape(original, quote=False) if escapar_html else original

        return _MARCADOR.sub(_trocar, texto)
