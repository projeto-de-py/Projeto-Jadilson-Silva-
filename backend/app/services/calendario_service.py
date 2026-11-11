"""Feriados nacionais para a contagem de prazos em dias uteis."""

from datetime import date

from app.integrations.brasilapi import BrasilAPIClient, Feriado


class CalendarioService:
    def __init__(self, brasilapi: BrasilAPIClient):
        self.brasilapi = brasilapi

    def feriados(self, ano: int) -> list[Feriado]:
        """Feriados nacionais de um ano, em ordem de data."""
        return sorted(self.brasilapi.feriados(ano), key=lambda f: f.data)

    def feriados_do_periodo(self, ano_inicial: int, quantidade_de_anos: int = 3) -> list[Feriado]:
        """Feriados de varios anos seguidos (um prazo longo pode cruzar a virada do ano)."""
        quantidade_de_anos = max(1, min(quantidade_de_anos, 5))
        todos: list[Feriado] = []
        for ano in range(ano_inicial, ano_inicial + quantidade_de_anos):
            todos.extend(self.feriados(ano))
        return todos

    def eh_feriado(self, dia: date) -> bool:
        return any(f.data == dia for f in self.feriados(dia.year))
