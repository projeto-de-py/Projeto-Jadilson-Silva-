"""Data/hora local do escritorio (America/Sao_Paulo) sem depender de tzdata.

O Brasil nao possui mais horario de verao desde 2019, entao o fuso do
escritorio e FIXO em UTC-3 durante todo o ano - um offset constante e exato
aqui, ao contrario de `zoneinfo.ZoneInfo("America/Sao_Paulo")`, que exige o
pacote `tzdata` (indisponivel neste ambiente).

Regra da Fase 4: classificacao de vencimento e agenda usam sempre a data
local do escritorio, evitando divergencias entre UTC e horario de Brasilia.
Os campos de auditoria (criado_em etc.) continuam em UTC via `utcnow()`.
"""

from datetime import date, datetime, timedelta, timezone

BRASILIA = timezone(timedelta(hours=-3))


def agora_brasilia() -> datetime:
    """Data/hora local atual, sem fuso (naive) - horario do escritorio."""
    return datetime.now(BRASILIA).replace(tzinfo=None)


def hoje_brasilia() -> date:
    """Data local de Brasilia usada em todo calculo de vencimento/agenda."""
    return agora_brasilia().date()
