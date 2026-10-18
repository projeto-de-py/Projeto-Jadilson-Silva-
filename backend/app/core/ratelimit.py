"""Rate limiting por janela deslizante (em memoria).

Portado do Sistema B para a arquitetura em camadas (fica em core/ pois e
infraestrutura transversal, sem regra de negocio).

Limitacao: estado em memoria - execute um unico worker uvicorn em producao
(uvicorn --workers 1) ou troque por Redis se precisar de multiplos workers.
"""

import time
from collections import deque
from threading import Lock

from fastapi import HTTPException


class Limiter:
    """Janela deslizante limitada em memoria (thread-safe)."""

    MAX_BUCKETS = 10_000  # evita crescimento ilimitado de memoria

    def __init__(self) -> None:
        self._buckets: dict[str, deque] = {}
        self._lock = Lock()

    def reset(self) -> None:
        """Zera todos os contadores (util em testes)."""
        with self._lock:
            self._buckets.clear()

    def _manter_buckets(self, janela: int) -> None:
        """Expulsa buckets vencidos quando a memoria esta cheia."""
        agora = time.monotonic()
        if len(self._buckets) < self.MAX_BUCKETS:
            return
        self._buckets = {
            k: v for k, v in self._buckets.items() if v and v[-1] > agora - janela
        }

    def _bucket(self, chave: str, janela: int) -> deque:
        """Retorna o bucket da chave, descartando tentativas ja vencidas."""
        agora = time.monotonic()
        bucket = self._buckets.setdefault(chave, deque())
        while bucket and bucket[0] <= agora - janela:
            bucket.popleft()
        return bucket

    def check(self, chave: str, limite: int, janela: int = 300) -> None:
        """Registra uma tentativa e lanca 429 se o limite da janela for excedido.

        Args:
            chave: identificador do bucket (ex.: "ip:127.0.0.1", "email:<hash>").
            limite: maximo de tentativas permitidas na janela.
            janela: tamanho da janela em segundos (padrao: 5 minutos).
        """
        with self._lock:
            self._manter_buckets(janela)
            if (
                len(self._buckets) >= self.MAX_BUCKETS
                and chave not in self._buckets
            ):
                self._limite_atingido(janela)

            bucket = self._bucket(chave, janela)
            if len(bucket) >= limite:
                self._limite_atingido(janela)
            bucket.append(time.monotonic())

    def bloqueado(self, chave: str, limite: int, janela: int = 300) -> None:
        """Apenas verifica o limite (NAO registra). Lanca 429 se ja estourado.

        Usado para o rate limit por e-mail no login: verifica antes de autenticar
        e so registra a tentativa quando a autenticacao falhar (evita bloquear a
        conta de um usuario valido por logins bem-sucedidos).
        """
        with self._lock:
            bucket = self._bucket(chave, janela)
            if len(bucket) >= limite:
                self._limite_atingido(janela)

    def registrar(self, chave: str, janela: int = 300) -> None:
        """Registra uma tentativa SEM checar limite (chamar apos falha de login)."""
        with self._lock:
            self._manter_buckets(janela)
            if (
                len(self._buckets) >= self.MAX_BUCKETS
                and chave not in self._buckets
            ):
                return  # memoria cheia: melhor nao registrar do que derrubar
            self._bucket(chave, janela).append(time.monotonic())

    def limpar(self, chave: str) -> None:
        """Remove o bucket da chave (ex.: apos login bem-sucedido)."""
        with self._lock:
            self._buckets.pop(chave, None)

    @staticmethod
    def _limite_atingido(janela: int) -> None:
        raise HTTPException(
            429,
            "Muitas tentativas. Aguarde e tente novamente.",
            headers={"Retry-After": str(janela)},
        )
