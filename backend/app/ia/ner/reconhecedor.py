"""Reconhecedor de entidades jurídicas (NER), treinado pela equipe com o LeNER-Br.

Dado um texto, devolve os trechos que são PESSOA, ORGANIZACAO, LEGISLACAO, JURISPRUDENCIA,
TEMPO ou LOCAL, com a posição no texto e uma confiança de 0 a 1.

  1. o texto vira palavras (tokenizador.py);
  2. cada palavra recebe atributos: ela mesma, as vizinhas, o formato (atributos.py);
  3. uma regressão logística dá, para cada palavra, a probabilidade de cada etiqueta BIO
     (B-PESSOA, I-PESSOA, O...);
  4. etiquetas seguidas do mesmo tipo viram uma entidade; a confiança é a média delas.

Escolhido por rodar em CPU comum em milissegundos e dar probabilidade por palavra, que é o
que a tela precisa para mostrar a faixa de confiança. Cada palavra é classificada
separadamente, então entidades muito longas podem quebrar (ver ai-model/README.md).
"""

from dataclasses import dataclass
from pathlib import Path

from app.ia.ner.atributos import atributos_da_frase
from app.ia.ner.tokenizador import Token, tokenizar

TIPOS = ("PESSOA", "ORGANIZACAO", "LEGISLACAO", "JURISPRUDENCIA", "TEMPO", "LOCAL")

LIMITE_ALTA = 0.90
LIMITE_MEDIA = 0.60


def faixa_de_confianca(confianca: float) -> str:
    if confianca >= LIMITE_ALTA:
        return "alta"
    if confianca >= LIMITE_MEDIA:
        return "media"
    return "baixa"


@dataclass(frozen=True)
class Entidade:
    tipo: str
    texto: str
    inicio: int
    fim: int
    confianca: float

    @property
    def faixa(self) -> str:
        return faixa_de_confianca(self.confianca)


@dataclass
class _Trecho:
    tipo: str
    primeiro: int
    ultimo: int
    confiancas: list[float]


def agrupar_entidades(etiquetas: list[tuple[str, float]], tokens: list[Token], texto: str) -> list[Entidade]:
    """Junta etiquetas BIO consecutivas em entidades, com as posições no `texto` original."""
    trechos: list[_Trecho] = []
    for i, (etiqueta, probabilidade) in enumerate(etiquetas):
        if etiqueta == "O":
            continue
        prefixo, tipo = etiqueta.split("-", 1)
        anterior = trechos[-1] if trechos else None
        if prefixo == "I" and anterior and anterior.tipo == tipo and anterior.ultimo == i - 1:
            anterior.ultimo = i
            anterior.confiancas.append(probabilidade)
        else:  # B-X, ou I-X sem B-X antes (o modelo errou o prefixo)
            trechos.append(_Trecho(tipo, i, i, [probabilidade]))

    entidades = []
    for t in trechos:
        inicio, fim = tokens[t.primeiro].inicio, tokens[t.ultimo].fim
        confianca = sum(t.confiancas) / len(t.confiancas)
        entidades.append(Entidade(t.tipo, texto[inicio:fim], inicio, fim, confianca))
    return entidades


class ReconhecedorEntidades:
    def __init__(self, conjunto: str = "completo", alpha: float = 1e-6, min_freq: int = 3, semente: int = 42, max_iter: int = 100):
        self.conjunto = conjunto
        self.alpha = alpha  # regularização: menor = ajusta mais aos exemplos
        self.min_freq = min_freq  # descarta atributos raros: modelo menor
        self.semente = semente
        self.max_iter = max_iter
        self.vetorizador = None
        self.classificador = None

    def treinar(self, frases: list[tuple[list[str], list[str]]]) -> "ReconhecedorEntidades":
        """`frases`: lista de (palavras, etiquetas BIO)."""
        from sklearn.feature_extraction import DictVectorizer
        from sklearn.linear_model import SGDClassifier

        atributos, etiquetas = [], []
        for palavras, etiquetas_da_frase in frases:
            atributos += atributos_da_frase(palavras, self.conjunto)
            etiquetas += etiquetas_da_frase

        vetorizador = DictVectorizer(sparse=True)
        X = vetorizador.fit_transform(atributos)
        frequentes = X.getnnz(axis=0) >= self.min_freq
        vetorizador.restrict(frequentes)

        self.vetorizador = vetorizador
        self.classificador = SGDClassifier(
            loss="log_loss", alpha=self.alpha, max_iter=self.max_iter, tol=1e-4, random_state=self.semente
        ).fit(X[:, frequentes], etiquetas)
        return self

    def etiquetar(self, palavras: list[str]) -> list[tuple[str, float]]:
        """Etiqueta mais provável de cada palavra e a probabilidade dela."""
        if self.classificador is None:
            raise RuntimeError("Modelo não treinado.")
        if not palavras:
            return []
        X = self.vetorizador.transform(atributos_da_frase(palavras, self.conjunto))
        probabilidades = self.classificador.predict_proba(X)
        classes = self.classificador.classes_
        return [(str(classes[k]), float(linha[k])) for linha, k in zip(probabilidades, probabilidades.argmax(axis=1), strict=True)]

    def extrair(self, texto: str) -> list[Entidade]:
        tokens = tokenizar(texto)
        etiquetas = self.etiquetar([t.texto for t in tokens])
        return agrupar_entidades(etiquetas, tokens, texto)

    def salvar(self, caminho: Path) -> None:
        import joblib

        caminho.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, caminho, compress=3)

    @staticmethod
    def carregar(caminho: Path) -> "ReconhecedorEntidades":
        import joblib

        return joblib.load(caminho)
