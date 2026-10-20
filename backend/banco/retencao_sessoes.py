"""Planejamento de retencao: somente SELECT; nunca remove registros.

Uso: python banco/retencao_sessoes.py --dias 30
A remocao fica no SQL comentado 003, sujeita a autorizacao e backup.
"""
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import Config
from database import Database

COUNT_EXPIRED = "SELECT COUNT(*) AS quantidade FROM sessoes WHERE expira_em < %s"


def planejar_limpeza(db, dias=30, *, agora=None):
    if isinstance(dias, bool) or not isinstance(dias, int) or not 7 <= dias <= 3650:
        raise ValueError("Retencao deve estar entre 7 e 3650 dias")
    now = agora if agora is not None else datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Horario de referencia deve incluir fuso")
    cutoff = (now.astimezone(timezone.utc) - timedelta(days=dias)).replace(tzinfo=None)
    row = db.one(COUNT_EXPIRED, (cutoff,))
    return {"modo": "somente_leitura", "retencao_dias": dias,
            "limite_utc": cutoff.isoformat(), "candidatas": row["quantidade"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dias", type=int, default=30)
    args = parser.parse_args()
    try:
        report = planejar_limpeza(Database(Config.load()), args.dias)
    except (ValueError, RuntimeError):
        parser.exit(2, "Configuracao de retencao invalida; revise os parametros.\n")
    except Exception:
        parser.exit(1, "Nao foi possivel consultar a retencao; nenhum registro removido.\n")
    for key, value in report.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
