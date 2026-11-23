"""Serviço do reconhecedor de entidades dentro do app: carrega o modelo uma vez e o usa.

O modelo é o arquivo ai-model/models/ner_juridico.joblib, gerado por
`python ai-model/scripts/treinar_ner.py`. Sem ele (ou sem scikit-learn) o app continua
funcionando: só os recursos de entidades ficam indisponíveis e respondem 503.
"""

import contextlib
import hashlib
import json
import threading
from functools import cached_property, lru_cache
from pathlib import Path

from app.ia.ner.reconhecedor import LIMITE_MEDIA, Entidade, ReconhecedorEntidades

CAMINHO_PADRAO = Path(__file__).resolve().parents[4] / "ai-model" / "models" / "ner_juridico.joblib"


class ModeloIndisponivelError(RuntimeError):
    """O modelo não está disponível neste servidor (arquivo ausente ou dependência faltando)."""


class ServicoEntidades:
    def __init__(self, caminho: Path | None = None):
        self.caminho = Path(caminho) if caminho else CAMINHO_PADRAO
        self._modelo: ReconhecedorEntidades | None = None
        self._trava = threading.Lock()

    def disponivel(self) -> bool:
        return self.caminho.exists()

    def _carregar(self) -> ReconhecedorEntidades:
        if self._modelo is not None:
            return self._modelo
        with self._trava:
            if self._modelo is None:
                self._modelo = self._ler_arquivo()
        return self._modelo

    def _ler_arquivo(self) -> ReconhecedorEntidades:
        if not self.caminho.exists():
            raise ModeloIndisponivelError(
                "O modelo de entidades ainda não foi gerado. Rode: python ai-model/scripts/treinar_ner.py"
            )
        try:
            return ReconhecedorEntidades.carregar(self.caminho)
        except ImportError as exc:
            raise ModeloIndisponivelError(
                "Dependências do modelo ausentes. Rode: pip install -r ai-model/requirements.txt"
            ) from exc

    @cached_property
    def versao(self) -> str:
        """Hash curto do arquivo do modelo + F1 de teste, quando há métricas ao lado dele."""
        if not self.caminho.exists():
            return "indisponivel"
        resumo = hashlib.sha1(self.caminho.read_bytes()).hexdigest()[:8]
        f1 = ""
        metricas = self.caminho.with_name("metricas_ner.json")
        with contextlib.suppress(OSError, ValueError, KeyError):
            f1 = f"-f1_{json.loads(metricas.read_text(encoding='utf-8'))['teste']['f1']}"
        return f"ner-{resumo}{f1}"

    def extrair(self, texto: str) -> list[Entidade]:
        return self._carregar().extrair(texto)

    def mascarar_nomes(self, texto: str, confianca_minima: float = LIMITE_MEDIA) -> str:
        pessoas = [e for e in self.extrair(texto) if e.tipo == "PESSOA" and e.confianca >= confianca_minima]
        for pessoa in reversed(pessoas):  # do fim para o começo: as posições anteriores não se deslocam
            texto = texto[: pessoa.inicio] + "[NOME]" + texto[pessoa.fim :]
        return texto


@lru_cache(maxsize=1)
def obter_servico() -> ServicoEntidades:
    return ServicoEntidades()
