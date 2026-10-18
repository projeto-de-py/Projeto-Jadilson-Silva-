"""Revogacao de tokens JWT (blocklist de `jti` em memoria).

Motivacao: o logout do cliente nao apaga o JWT do servidor - ele so some do
browser. Sem revogacao, um token roubado continuaria autenticando por ate 8h
mesmo apos a vitima deslogar. Aqui guardamos o `jti` de tokens deslogados e o
`get_current_user` rejeita sessoes revogadas.

Limitacao (mesma do rate limit em core/ratelimit.py): estado em memoria, logo
valem as mesmas restricoes - rode um unico worker uvicorn em producao ou troque
por Redis se precisar de multiplos workers. Reiniciar o servidor limpa a
blocklist, mas um token so sobrevive ate a propria expiracao (8h).
"""

import time
from threading import Lock


class TokenRevogados:
    """Blocklist thread-safe de `jti`, com expiracao propria."""

    MAX_TOKENS = 50_000  # evita crescimento ilimitado de memoria

    def __init__(self) -> None:
        self._tokens: dict[str, float] = {}
        self._lock = Lock()

    def revogar(self, jti: str | None, exp: float | None = None) -> None:
        """Marca um `jti` como invalido ate o proprio `exp` (epoch segundos)."""
        if not jti:
            return
        horario_limite = float(exp) if exp else time.time() + 3600
        with self._lock:
            self._descartar_vencidos()
            if len(self._tokens) >= self.MAX_TOKENS:
                # valvula de seguranca: nunca cresce sem limite
                self._tokens.clear()
            self._tokens[jti] = horario_limite

    def esta_revogado(self, jti: str | None) -> bool:
        """True se o `jti` foi deslogado e ainda nao expirou."""
        if not jti:
            return False
        with self._lock:
            horario_limite = self._tokens.get(jti)
            if horario_limite is None:
                return False
            if horario_limite <= time.time():
                del self._tokens[jti]  # ja expirou sozinho, descarta
                return False
            return True

    def _descartar_vencidos(self) -> None:
        agora = time.time()
        for jti in [k for k, v in self._tokens.items() if v <= agora]:
            del self._tokens[jti]

    def reset(self) -> None:
        """Zera a blocklist (util em testes)."""
        with self._lock:
            self._tokens.clear()
