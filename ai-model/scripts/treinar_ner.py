"""Treina e AVALIA o reconhecedor de entidades jurídicas (NER) com o LeNER-Br.

  1. lê train/dev/test (python ai-model/scripts/baixar_lener.py);
  2. baseline: "dicionário", que decora as entidades do treino e as procura no teste;
  3. experimento: 3 conjuntos de atributos x 2 forças de regularização, comparados no dev;
  4. a melhor configuração do dev é medida UMA vez no teste (precisão, revocação, F1);
  5. análise de erros, modelo salvo em ai-model/models/ e métricas em metricas_ner.json.

A semente é fixa (42): a mesma execução dá o mesmo resultado.

Uso:  python ai-model/scripts/treinar_ner.py
"""

import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "backend"))  # usa o mesmo código de atributos e tokenização do app

from seqeval.metrics import classification_report, f1_score, precision_score, recall_score  # noqa: E402

from app.ia.ner.atributos import CONJUNTOS  # noqa: E402
from app.ia.ner.reconhecedor import TIPOS, ReconhecedorEntidades  # noqa: E402

DADOS = RAIZ / "datasets" / "lener_br"
MODELO = RAIZ / "ai-model" / "models" / "ner_juridico.joblib"
METRICAS = RAIZ / "ai-model" / "models" / "metricas_ner.json"
ALPHAS = (1e-7, 1e-6)  # 1e-5 já foi testado e piorou o resultado
EXEMPLOS_DE_ERRO = 12

Frase = tuple[list[str], list[str]]  # (palavras, etiquetas BIO)


def ler_conll(caminho: Path) -> list[Frase]:
    frases, palavras, etiquetas = [], [], []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if linha.strip():
            partes = linha.split()
            palavras.append(partes[0])
            etiquetas.append(partes[-1])
        elif palavras:
            frases.append((palavras, etiquetas))
            palavras, etiquetas = [], []
    if palavras:
        frases.append((palavras, etiquetas))
    return frases


def trechos(etiquetas: list[str]) -> set[tuple[str, int, int]]:
    """Entidades de uma frase como (tipo, primeira palavra, última palavra)."""
    achados, inicio, tipo = set(), None, None
    for i, etiqueta in enumerate([*etiquetas, "O"]):
        mudou = etiqueta == "O" or etiqueta.startswith("B-") or etiqueta[2:] != tipo
        if inicio is not None and mudou:
            achados.add((tipo, inicio, i - 1))
            inicio = None
        if etiqueta != "O" and inicio is None:
            inicio, tipo = i, etiqueta[2:]
    return achados


class BaselineDicionario:
    """Decora cada entidade do treino e marca o que for igual no texto (a mais longa primeiro)."""

    def __init__(self, frases: list[Frase]):
        self.conhecidas: dict[tuple[str, ...], str] = {}
        for palavras, etiquetas in frases:
            for tipo, a, b in trechos(etiquetas):
                self.conhecidas[tuple(p.lower() for p in palavras[a : b + 1])] = tipo
        self.maior = max(len(k) for k in self.conhecidas)

    def prever(self, palavras: list[str]) -> list[str]:
        baixas = [p.lower() for p in palavras]
        etiquetas, i = ["O"] * len(palavras), 0
        while i < len(palavras):
            tamanho = next((n for n in range(min(self.maior, len(palavras) - i), 0, -1) if tuple(baixas[i : i + n]) in self.conhecidas), 0)
            if not tamanho:
                i += 1
                continue
            tipo = self.conhecidas[tuple(baixas[i : i + tamanho])]
            etiquetas[i : i + tamanho] = ["B-" + tipo] + ["I-" + tipo] * (tamanho - 1)
            i += tamanho
        return etiquetas


def metricas(gabarito: list[list[str]], previsto: list[list[str]]) -> dict[str, float]:
    return {
        "precisao": round(float(precision_score(gabarito, previsto)), 4),
        "revocacao": round(float(recall_score(gabarito, previsto)), 4),
        "f1": round(float(f1_score(gabarito, previsto)), 4),
    }


def etiquetas_do_gabarito(frases: list[Frase]) -> list[list[str]]:
    return [etiquetas for _, etiquetas in frases]


def prever(modelo: ReconhecedorEntidades, frases: list[Frase]) -> list[list[str]]:
    return [[etiqueta for etiqueta, _ in modelo.etiquetar(palavras)] for palavras, _ in frases]


def analisar_erros(frases: list[Frase], previsto: list[list[str]]) -> dict:
    """Entidades que o modelo deixou passar (falsos negativos) e que inventou (falsos positivos)."""
    perdidos, inventados = [], []
    for (palavras, gabarito), previstas in zip(frases, previsto, strict=True):
        certas, achadas = trechos(gabarito), trechos(previstas)
        perdidos += [{"tipo": t, "texto": " ".join(palavras[a : b + 1])} for t, a, b in sorted(certas - achadas)]
        inventados += [{"tipo": t, "texto": " ".join(palavras[a : b + 1])} for t, a, b in sorted(achadas - certas)]
    return {
        "falsos_negativos": len(perdidos),
        "falsos_positivos": len(inventados),
        "exemplos_falsos_negativos": perdidos[:EXEMPLOS_DE_ERRO],
        "exemplos_falsos_positivos": inventados[:EXEMPLOS_DE_ERRO],
    }


def avaliar_baseline(treino: list[Frase], dev: list[Frase], teste: list[Frase]) -> dict:
    baseline = BaselineDicionario(treino)
    resultado = {
        nome: metricas(etiquetas_do_gabarito(frases), [baseline.prever(p) for p, _ in frases])
        for nome, frases in (("dev", dev), ("teste", teste))
    }
    print("baseline (dicionário), teste:", resultado["teste"])
    return resultado


def comparar_configuracoes(treino: list[Frase], dev: list[Frase]) -> tuple[list[dict], ReconhecedorEntidades]:
    """Treina cada combinação e devolve a tabela de resultados e o melhor modelo (escolhido no dev)."""
    tabela, melhor = [], None
    for conjunto in CONJUNTOS:
        for alpha in ALPHAS:
            inicio = time.time()
            modelo = ReconhecedorEntidades(conjunto=conjunto, alpha=alpha).treinar(treino)
            resultado = metricas(etiquetas_do_gabarito(dev), prever(modelo, dev))
            tabela.append({"atributos": conjunto, "alpha": alpha, **resultado, "segundos": round(time.time() - inicio)})
            print(f"  {conjunto:9s} alpha={alpha:g}  dev F1={resultado['f1']:.4f}")
            if melhor is None or resultado["f1"] > melhor[0]:
                melhor = (resultado["f1"], modelo)
    return tabela, melhor[1]


def avaliar_no_teste(modelo: ReconhecedorEntidades, teste: list[Frase]) -> dict:
    gabarito, previsto = etiquetas_do_gabarito(teste), prever(modelo, teste)
    por_tipo = classification_report(gabarito, previsto, output_dict=True)
    print(classification_report(gabarito, previsto, digits=3))
    return {
        "escolhido": {"atributos": modelo.conjunto, "alpha": modelo.alpha},
        "teste": metricas(gabarito, previsto),
        "teste_por_entidade": {
            tipo: {k: round(v, 4) for k, v in por_tipo[tipo].items() if k != "support"} | {"exemplos": int(por_tipo[tipo]["support"])}
            for tipo in TIPOS
        },
        "erros": analisar_erros(teste, previsto),
    }


def main() -> None:
    treino, dev, teste = (ler_conll(DADOS / f"{parte}.conll") for parte in ("train", "dev", "test"))
    print(f"frases: treino={len(treino)} dev={len(dev)} teste={len(teste)}")

    tabela, modelo = comparar_configuracoes(treino, dev)
    resultado = {
        "semente": 42,
        "frases": {"treino": len(treino), "dev": len(dev), "teste": len(teste)},
        "baseline_dicionario": avaliar_baseline(treino, dev, teste),
        "experimentos_dev": tabela,
        **avaliar_no_teste(modelo, teste),
    }

    modelo.salvar(MODELO)
    METRICAS.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"teste: {resultado['teste']}\nmodelo: {MODELO} ({MODELO.stat().st_size / 1e6:.1f} MB)\nmétricas: {METRICAS}")


if __name__ == "__main__":
    main()
