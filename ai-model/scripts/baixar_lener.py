"""Baixa o LeNER-Br (reconhecimento de entidades em textos jurídicos em português).

Fonte oficial: https://github.com/peluz/lener-br  (licença MIT)
Artigo: LUZ DE ARAUJO, P. H. et al. LeNER-Br: a Dataset for Named Entity Recognition in
Brazilian Legal Text. PROPOR 2018. https://cic.unb.br/~teodecampos/LeNER-Br/

Conteúdo: 66 decisões de tribunais (STF, STJ, TJMG, TCU...) e 4 leis, anotadas à mão com
as etiquetas ORGANIZACAO, PESSOA, TEMPO, LOCAL, LEGISLACAO e JURISPRUDENCIA (formato BIO).

Uso:  python ai-model/scripts/baixar_lener.py
"""

import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/peluz/lener-br/master/leNER-Br"
PARTES = ("train", "dev", "test")
DESTINO = Path(__file__).resolve().parents[2] / "datasets" / "lener_br"


def baixar() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    for parte in PARTES:
        saida = DESTINO / f"{parte}.conll"
        with urllib.request.urlopen(f"{BASE}/{parte}/{parte}.conll", timeout=60) as resp:
            saida.write_bytes(resp.read())
        print(f"{parte}: {saida.stat().st_size / 1e6:.2f} MB -> {saida}")


if __name__ == "__main__":
    baixar()
