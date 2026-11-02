"""Cache em memoria com validade, para nao repetir a mesma consulta a uma API externa.

Uso tipico (dentro de um cliente):

    cache = CacheTTL()
    cache.guardar("feriados:2026", lista, ttl_segundos=30 * 24 * 3600)
    lista = cache.obter("feriados:2026")   # None se nao existe ou venceu

Limitacao: vive na memoria de UM processo. Com varios workers cada um tem o seu cache
(so custa uma chamada a mais por worker). Para compartilhar, troque por Redis mantendo
estes mesmos tres metodos.
"""

import time
from threading import Lock
from typing import Any


class CacheTTL:
    """Cache chave -> valor com tempo de vida e tamanho maximo (descarta o mais antigo)."""

    def __init__(self, max_itens: int = 512) -> None:
        self._max = max_itens
        self._dados: dict[str, tuple[float, Any]] = {}
        self._lock = Lock()

    def obter(self, chave: str) -> Any | None:
        with self._lock:
            achado = self._dados.get(chave)
            if achado is None:
                return None
            vence_em, valor = achado
            if vence_em < time.monotonic():
                del self._dados[chave]
                return None
            return valor

    def guardar(self, chave: str, valor: Any, ttl_segundos: float) -> None:
        with self._lock:
            if len(self._dados) >= self._max and chave not in self._dados:
                mais_antiga = min(self._dados, key=lambda k: self._dados[k][0])
                del self._dados[mais_antiga]
            self._dados[chave] = (time.monotonic() + ttl_segundos, valor)

    def limpar(self) -> None:
        with self._lock:
            self._dados.clear()
