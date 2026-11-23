"""Anonimização por regras de textos jurídicos públicos (LGPD: minimização).

Mesmo sendo decisões públicas, tudo que identifica pessoas sai antes de gravar qualquer
linha em disco. Sem reconhecimento de nomes, nomes soltos no meio de frases podem passar;
por isso `auditar` mede o que sobrou e o risco residual é declarado no relatório.
"""

import re
from dataclasses import dataclass


@dataclass
class Auditoria:
    """Quanto ainda parece dado pessoal depois da anonimização."""

    cpf: int = 0
    cnpj: int = 0
    email: int = 0
    telefone: int = 0
    numero_cnj: int = 0
    linhas_de_parte: int = 0

    @property
    def total(self) -> int:
        return self.cpf + self.cnpj + self.email + self.telefone + self.numero_cnj + self.linhas_de_parte


class Anonimizador:
    _CNJ = re.compile(r"\b\d{7}-?\d{2}\.?\d{4}\.?\d\.?\d{2}\.?\d{4}\b")
    _CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
    _CNPJ = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
    _EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
    _FONE = re.compile(r"(?<!\d)(?:\(?\d{2}\)?\s?)?9?\d{4}[-\s]\d{4}(?!\d)")
    _OAB = re.compile(r"\bOAB[/\s-]*[A-Z]{2}\s*[\d.]+\b", re.I)
    # Cabeçalho com o nome das partes: "AGRAVANTE: FULANO DE TAL"
    _LINHA_PARTE = re.compile(r"^\s*[A-ZÀ-Ú][A-ZÀ-Ú /.\-()]{2,40}:\s*\S.*$", re.M)
    # Texto corrido: "em que é Agravante FULANO e Agravado CICLANO"
    _PARTE_NO_TEXTO = re.compile(
        r"(?:agravante|agravad[oa]|recorrente|recorrid[oa]|reclamante|reclamad[oa])s?"
        r"\s+(?:[A-ZÀ-Ú][\wÀ-ú.&'-]*\s*(?:DE|DA|DO|DOS|DAS|E|S\.A\.?)?\s*){1,6}",
    )
    _LINHA_NUMERADA = re.compile(r"^.*N[ºo°]\s*\d.*$", re.M)
    _LINHA_DE_DATA = re.compile(r"^.*\b\d{1,2} de [a-zç]+ de \d{4}\.?\s*$", re.M | re.I)
    _HTML = re.compile(r"<[^>]+>")

    def anonimizar(self, texto: str) -> str:
        t = texto or ""
        for linha in (self._LINHA_PARTE, self._LINHA_NUMERADA, self._LINHA_DE_DATA):
            t = linha.sub("", t)
        for padrao, marcador in (
            (self._CNJ, "[PROCESSO]"),
            (self._CNPJ, "[CNPJ]"),
            (self._CPF, "[CPF]"),
            (self._EMAIL, "[EMAIL]"),
            (self._OAB, "[OAB]"),
            (self._FONE, "[TELEFONE]"),
            (self._PARTE_NO_TEXTO, "[PARTE]"),
            (self._HTML, " "),
        ):
            t = padrao.sub(marcador, t)
        return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", t)).strip()

    def auditar(self, texto: str) -> Auditoria:
        """Conta identificadores que ainda aparecem (deve ser perto de zero após anonimizar)."""
        return Auditoria(
            cpf=len(self._CPF.findall(texto)),
            cnpj=len(self._CNPJ.findall(texto)),
            email=len(self._EMAIL.findall(texto)),
            telefone=len(self._FONE.findall(texto)),
            numero_cnj=len(self._CNJ.findall(texto)),
            linhas_de_parte=len(self._LINHA_PARTE.findall(texto)),
        )
