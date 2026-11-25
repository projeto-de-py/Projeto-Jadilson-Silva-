"""Protótipo de coleta de ementas públicas para um classificador de área jurídica.

A ideia do classificador foi descartada (o advogado já escolhe a área ao criar o documento),
mas o protótipo fica como experimento: mostra que os dados reais e públicos eram viáveis.

Fontes (Hugging Face, decisões públicas):
  TRABALHISTA     ementas do TST         celsowm/jurisprudencias_tst
  PREVIDENCIARIO  TRF2, competência ou assunto previdenciário
  BANCARIO        TRF2, assunto de contrato bancário ou financiamento

O rótulo vem dos METADADOS do tribunal, nunca de palavras do texto. Só `texto`, já
anonimizado, e `rotulo` vão para o CSV.

Uso:  python ai-model/scripts/coletar_dados.py --mb 60 --saida datasets/ementas_amostra.csv
"""

import argparse
import csv
import hashlib
import json
import re
import urllib.request
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

from anonimizar import Anonimizador

URL_HF = "https://huggingface.co/datasets/celsowm/{0}/resolve/main/{0}.json"
TAMANHO_MINIMO = 300
SEM_EMENTA = re.compile(r"^\s*(DESPACHO|DECIS[ÃA]O|ATO ORDINAT)", re.I)
Registro = tuple[str, str, str]  # (chave do documento, rótulo, texto bruto)


def transmitir_objetos(url: str, limite_mb: int) -> Iterator[dict]:
    """Lê um JSON gigante (lista de objetos) aos pedaços, sem carregá-lo inteiro na memória."""
    decodificador, pendente, lidos = json.JSONDecoder(), "", 0
    with urllib.request.urlopen(url, timeout=60) as resposta:
        while lidos < limite_mb * 1_000_000:
            pedaco = resposta.read(1 << 20)
            if not pedaco:
                return
            lidos += len(pedaco)
            pendente += pedaco.decode("utf-8", errors="ignore")
            consumido, posicao = 0, pendente.find("{")
            while posicao >= 0:
                try:
                    objeto, consumido = decodificador.raw_decode(pendente, posicao)
                except ValueError:
                    break  # objeto cortado no meio: espera o próximo pedaço
                yield objeto
                posicao = pendente.find("{", consumido)
            pendente = pendente[consumido:]


class FonteTST:
    url = URL_HF.format("jurisprudencias_tst")

    def registros(self, limite_mb: int) -> Iterator[Registro]:
        for objeto in transmitir_objetos(self.url, limite_mb):
            registro = objeto.get("registro", {})
            texto = registro.get("txtEmentaHighlight") or ""
            yield str(registro.get("id") or texto[:80]), "TRABALHISTA", texto


class FonteTRF2:
    url = URL_HF.format("jurisprudencias_trf2")
    _PREVIDENCIARIO = re.compile(r"previdenci|assist[eê]ncia social", re.I)
    _BANCARIO = re.compile(
        r"contratos? banc|^banc[aá]rios?$|c[eé]dula de cr[eé]dito banc|empr[eé]stimo consignado|"
        r"aliena[cç][aã]o fiduci|sistema financeiro da habita|cr[eé]dito direto ao consumidor",
        re.I,
    )

    def _rotular(self, objeto: dict) -> str | None:
        """Previdenciário, bancário ou None quando não for nenhum dos dois, ou for ambíguo."""
        assuntos = [a.strip() for a in re.split(r",\s*", objeto.get("Assunto(s)", ""))]
        previdenciario = bool(self._PREVIDENCIARIO.search(objeto.get("Competência", ""))) or "DIREITO PREVIDENCIÁRIO" in (
            a.upper() for a in assuntos
        )
        bancario = any(self._BANCARIO.search(a) for a in assuntos)
        if previdenciario == bancario:
            return None
        return "PREVIDENCIARIO" if previdenciario else "BANCARIO"

    def registros(self, limite_mb: int) -> Iterator[Registro]:
        for objeto in transmitir_objetos(self.url, limite_mb):
            rotulo = self._rotular(objeto)
            if rotulo:
                yield str(objeto.get("data_id")), rotulo, objeto.get("ementa", "")


class ColetorEmentas:
    def __init__(self) -> None:
        self.anonimizador = Anonimizador()

    def coletar(self, mb_por_fonte: int, saida: Path) -> None:
        vistos: set[str] = set()
        por_classe: Counter = Counter()
        descartes: Counter = Counter()
        vazamentos = 0
        saida.parent.mkdir(parents=True, exist_ok=True)
        with saida.open("w", newline="", encoding="utf-8") as arquivo:
            escritor = csv.writer(arquivo)
            escritor.writerow(["id", "fonte", "rotulo", "texto"])
            for nome, fonte in (("TST", FonteTST()), ("TRF2", FonteTRF2())):
                for chave, rotulo, bruto in fonte.registros(mb_por_fonte):
                    texto = self.anonimizador.anonimizar(bruto)
                    motivo = self._motivo_de_descarte(texto, vistos)
                    if motivo:
                        descartes[motivo] += 1
                        continue
                    vistos.add(texto)
                    vazamentos += self.anonimizador.auditar(texto).total
                    escritor.writerow([hashlib.sha1(chave.encode()).hexdigest()[:12], nome, rotulo, texto])
                    por_classe[rotulo] += 1
        print(f"Gravado em {saida}")
        print("Exemplos por classe:", dict(por_classe))
        print("Descartados:", dict(descartes))
        print("Identificadores restantes após anonimizar:", vazamentos)

    @staticmethod
    def _motivo_de_descarte(texto: str, vistos: set[str]) -> str | None:
        if len(texto) < TAMANHO_MINIMO:
            return "curto"
        if SEM_EMENTA.match(texto):
            return "despacho_sem_ementa"
        if texto in vistos:
            return "duplicado"
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Coleta ementas públicas anonimizadas")
    parser.add_argument("--mb", type=int, default=40, help="MB lidos de cada fonte")
    parser.add_argument("--saida", type=Path, default=Path("datasets/ementas_amostra.csv"))
    args = parser.parse_args()
    ColetorEmentas().coletar(args.mb, args.saida)
