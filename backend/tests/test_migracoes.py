"""Testes de migration Alembic (0003 da Fase 1 e 0004 da Fase 2) em SQLite.

Roda em subprocesso com DATABASE_URL apontando para um arquivo temporario,
para nao misturar o Alembic com a sessao de teste da aplicacao. Cobre:
upgrade com dados legados preservados (backfills), downgrade coerente e
re-upgrade.
"""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]

CONFERE = """
import os, sqlite3, sys
from alembic import command
from alembic.config import Config

db = os.environ["DATABASE_URL"].replace("sqlite:///", "")
cfg = Config("alembic.ini")


def consulta(sql, args=()):
    con = sqlite3.connect(db)
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


def tabelas():
    return {r[0] for r in consulta("SELECT name FROM sqlite_master WHERE type='table'")}


erros = []

# linhas do estado pre-Fase-1 (perfis antigos ADMIN/PADRAO precisam ser convertidos)
command.upgrade(cfg, "0002_casos_prazos")
con = sqlite3.connect(db)
con.execute(
    "INSERT INTO usuarios (nome, email, senha_hash, perfil, ativo, criado_em) "
    "VALUES ('Admin Antigo','adminantigo@x.adv','h','ADMIN',1,'2026-01-01 00:00:00')"
)
con.execute(
    "INSERT INTO usuarios (nome, email, senha_hash, perfil, ativo, criado_em) "
    "VALUES ('Padrao Antigo','padrao@x.adv','h','PADRAO',1,'2026-01-01 00:00:00')"
)
con.execute(
    "INSERT INTO casos (numero_processo, cliente, area, status, criado_em) "
    "VALUES ('1','Cliente X','Civel','EM_ANDAMENTO','2026-01-01 00:00:00')"
)
con.commit()
con.close()

command.upgrade(cfg, "head")

if not {"clientes", "usuario_casos"} <= tabelas():
    erros.append("tabelas da Fase 1 ausentes apos upgrade")

cols = {r[1] for r in consulta("PRAGMA table_info(usuarios)")}
if not {"administrador", "atualizado_em", "senha_hash"} <= cols:
    erros.append("colunas novas de usuarios ausentes")

cols_casos = {r[1] for r in consulta("PRAGMA table_info(casos)")}
if "cliente_id" not in cols_casos:
    erros.append("casos.cliente_id ausente")

linhas = consulta("SELECT email, perfil, administrador FROM usuarios ORDER BY email")
esperado = [("adminantigo@x.adv", "ADVOGADO", 1), ("padrao@x.adv", "ADVOGADO", 0)]
if linhas != esperado:
    erros.append(f"conversao de perfis inesperada: {linhas!r}")

ddl = consulta("SELECT sql FROM sqlite_master WHERE type='table' AND name='usuario_casos'")[0][0]
for trecho in ("uq_usuario_caso", "REFERENCES usuarios", "REFERENCES casos"):
    if trecho not in ddl:
        erros.append(f"usuario_casos sem {trecho}")

ddl_cli = consulta("SELECT sql FROM sqlite_master WHERE type='table' AND name='clientes'")[0][0]
if "uq_clientes_cpf_cnpj" not in ddl_cli:
    erros.append("UNIQUE de cpf_cnpj ausente")

# ------------------------------------------------------------ Fase 2 (0004)
if "caso_historicos" not in tabelas():
    erros.append("tabela caso_historicos ausente apos upgrade")

cols_c2 = {r[1]: r for r in consulta("PRAGMA table_info(casos)")}
fase2_cols = {
    "titulo", "tipo_demanda", "prioridade", "data_abertura", "responsavel_id",
    "observacoes", "arquivado", "arquivado_por", "arquivado_em", "criado_por",
    "atualizado_em",
}
if not fase2_cols <= set(cols_c2):
    erros.append(f"colunas da Fase 2 ausentes: {fase2_cols - set(cols_c2)}")

# numero_processo deixa de ser obrigatorio (notnull == 0 no PRAGMA)
if cols_c2.get("numero_processo") and cols_c2["numero_processo"][3] != 0:
    erros.append("numero_processo continua NOT NULL apos 0004")

# backfills: titulo = numero legado; data_abertura = data de criacao
titulo_legado, numero_legado, abertura = consulta(
    "SELECT titulo, numero_processo, data_abertura FROM casos"
)[0]
if titulo_legado != "1" or numero_legado != "1":
    erros.append(f"backfill de titulo/numero inesperado: {(titulo_legado, numero_legado)!r}")
if abertura != "2026-01-01":
    erros.append(f"backfill de data_abertura inesperado: {abertura!r}")

ddl_casos2 = consulta("SELECT sql FROM sqlite_master WHERE type='table' AND name='casos'")[0][0]
if "uq_casos_numero_processo" not in ddl_casos2:
    erros.append("UNIQUE de numero_processo perdido no batch_alter da 0004")

idxs = {r[0] for r in consulta("SELECT name FROM sqlite_master WHERE type='index'")}
fase2_idx = {
    "ix_casos_titulo", "ix_casos_tipo_demanda", "ix_casos_data_abertura",
    "ix_casos_responsavel_id", "ix_casos_arquivado", "ix_casos_area",
    "ix_caso_historicos_caso_id",
}
if not fase2_idx <= idxs:
    erros.append(f"indices da Fase 2 ausentes: {fase2_idx - idxs}")

# dois casos SEM numero nao podem colidir (UNIQUE ignora NULL)
con = sqlite3.connect(db)
for n in (1, 2):
    con.execute(
        "INSERT INTO casos (titulo, numero_processo, cliente, area, status, tipo_demanda, "
        "prioridade, data_abertura, arquivado, criado_em, atualizado_em) "
        "VALUES (?, NULL, ?, 'PREVIDENCIARIO', 'NOVO', 'ADMINISTRATIVA', 'MEDIA', "
        "'2026-03-01', 0, '2026-03-01 00:00:00', '2026-03-01 00:00:00')",
        (f"Sem processo {n}", f"Cliente Adm {n}"),
    )
con.commit()
nulos = con.execute("SELECT COUNT(*) FROM casos WHERE numero_processo IS NULL").fetchone()[0]
con.close()
if nulos != 2:
    erros.append(f"NULLs de numero_processo rejeitados indevidamente: {nulos}")


# ---------------------------------------------------------------- downgrade
command.downgrade(cfg, "0002_casos_prazos")

restantes = tabelas()
if {"clientes", "usuario_casos", "caso_historicos"} & restantes:
    erros.append("tabelas das Fases 1/2 nao foram removidas no downgrade")

cols2 = {r[1] for r in consulta("PRAGMA table_info(usuarios)")}
if {"administrador", "atualizado_em"} & cols2:
    erros.append("colunas novas nao foram removidas no downgrade")

cols_casos3 = {r[1]: r for r in consulta("PRAGMA table_info(casos)")}
if fase2_cols & set(cols_casos3):
    erros.append(f"colunas da Fase 2 nao removidas: {fase2_cols & set(cols_casos3)}")
# NOT NULL restaurado e casos sem numero viraram marcador reversivel
if cols_casos3.get("numero_processo") and cols_casos3["numero_processo"][3] == 0:
    erros.append("NOT NULL de numero_processo nao restaurado no downgrade")
marcadores = consulta(
    "SELECT COUNT(*) FROM casos WHERE numero_processo LIKE 'S/N-%'"
)[0][0]
if marcadores != 2:
    erros.append(f"marcador S/N aplicado em {marcadores} casos (esperado 2)")

linhas2 = consulta("SELECT email, perfil FROM usuarios ORDER BY email")
esperado2 = [("adminantigo@x.adv", "ADMIN"), ("padrao@x.adv", "PADRAO")]
if linhas2 != esperado2:
    erros.append(f"reversao de perfis inesperada: {linhas2!r}")

# nenhum registro legado foi perdido no caminho inteiro
total_usuarios = consulta("SELECT COUNT(*) FROM usuarios")[0][0]
if total_usuarios != 2:
    erros.append(f"usuarios perdidos durante a migracao: {total_usuarios}")
total_casos = consulta("SELECT COUNT(*) FROM casos")[0][0]
if total_casos != 3:
    erros.append(f"casos perdidos durante a migracao: {total_casos}")

# ------------------------------------------------------------- re-upgrade
command.upgrade(cfg, "head")
if "clientes" not in tabelas():
    erros.append("re-upgrade falhou")

print("ERROS:" if erros else "OK")
for e in erros:
    print(" -", e)
sys.exit(1 if erros else 0)
"""


def _rodar(database_url: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DATABASE_URL": database_url}
    return subprocess.run(
        [sys.executable, "-c", CONFERE],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


@pytest.fixture()
def db_file(tmp_path):
    return tmp_path / "migracao_test.db"


def test_upgrade_preserva_dados_e_downgrade_e_coerente(db_file):
    url = f"sqlite:///{db_file}"
    proc = _rodar(url)
    assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    assert "OK" in proc.stdout


def test_migration_e_repetivel(tmp_path):
    """Rodar o ciclo completo duas vezes (bancos diferentes) da o mesmo resultado."""
    for i in range(2):
        banco = tmp_path / f"repete_{i}.db"
        proc = _rodar(f"sqlite:///{banco}")
        assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
