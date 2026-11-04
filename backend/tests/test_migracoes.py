"""Testes de migration Alembic (0003 da Fase 1, 0004 da Fase 2, 0005 da
Fase 3, 0006 da Fase 4 e 0007 - permissao de compromissos) em SQLite.

Roda em subprocesso com DATABASE_URL apontando para um arquivo temporario,
para nao misturar o Alembic com a sessao de teste da aplicacao. Cobre:
upgrade com dados legados preservados (backfills), downgrade coerente (por
fase) e re-upgrade. A Fase 3 valida o backfill seletivo de processos
judiciais a partir de `casos.numero_processo` (somente numeros CNJ-validos);
a Fase 4 valida o backfill reversivel de prazos e a 0007 valida a nova
permissao `pode_gerenciar_compromissos` (default False, sem backfill).
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
# caso com numero CNJ VALIDO (modulo 97): deve virar processo na Fase 3
con.execute(
    "INSERT INTO casos (numero_processo, cliente, area, status, tribunal, vara, criado_em) "
    "VALUES ('0004567-89.2023.8.26.0050','Cliente Valido','Civel','EM_ANDAMENTO',"
    "'TJSP','1a Vara','2026-01-02 00:00:00')"
)
# prazos legados (Fase 4): precisam sobreviver ao backfill com os MESMOS
# valores, apenas com os campos renomeados/derivados.
con.execute(
    "INSERT INTO prazos (caso_id, titulo, tipo, data_limite, descricao, cumprido, criado_em) "
    "VALUES (1, 'Prazo legado cumprido', 'PROCESSUAL', '2026-11-20', 'legado', 1, "
    "'2026-01-01 00:00:00')"
)
con.execute(
    "INSERT INTO prazos (caso_id, titulo, tipo, data_limite, descricao, cumprido, criado_em) "
    "VALUES (1, 'Prazo legado aberto', 'PROCESSUAL', '2026-12-01', NULL, 0, "
    "'2026-01-02 00:00:00')"
)
con.commit()
con.close()

# Fase 2 antes da final: casos.responsavel_id precisa existir para o
# backfill de responsavel da 0006 herdar o responsavel do caso.
command.upgrade(cfg, "0004_casos_gestao")
con = sqlite3.connect(db)
con.execute("UPDATE casos SET responsavel_id = 1 WHERE id = 1")
con.commit()
con.close()

# linha de permissao criada ANTES da 0007: precisa nascer com a nova
# coluna em False (nenhum privilegio concedido automaticamente).
command.upgrade(cfg, "0006_prazos_compromissos")
con = sqlite3.connect(db)
con.execute(
    "INSERT INTO usuario_casos (usuario_id, caso_id, pode_visualizar, "
    "pode_gerenciar_prazos, ativo, concedido_em) "
    "VALUES (2, 1, 1, 1, 1, '2026-01-01 00:00:00')"
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

# ------------------------------------------------------------ Fase 3 (0005)
if not {"processos_judiciais", "processo_historicos"} <= tabelas():
    erros.append("tabelas da Fase 3 ausentes apos upgrade")

cols_p3 = {r[1] for r in consulta("PRAGMA table_info(processos_judiciais)")}
fase3_cols = {
    "id", "caso_id", "numero_processo", "tribunal", "orgao_julgador", "comarca",
    "instancia", "classe_processual", "assunto", "data_distribuicao", "status",
    "valor_causa", "segredo_justica", "observacoes", "arquivado", "arquivado_por",
    "arquivado_em", "criado_por", "criado_em", "atualizado_em",
}
if not fase3_cols <= cols_p3:
    erros.append(f"colunas da Fase 3 ausentes: {fase3_cols - cols_p3}")

cols_uc3 = {r[1] for r in consulta("PRAGMA table_info(usuario_casos)")}
if "pode_gerenciar_processos" not in cols_uc3:
    erros.append("usuario_casos.pode_gerenciar_processos ausente")
# 0007: permissao propria de compromissos, SEM backfill de privilegio
if "pode_gerenciar_compromissos" not in cols_uc3:
    erros.append("usuario_casos.pode_gerenciar_compromissos ausente (0007)")
concedidos = consulta(
    "SELECT COUNT(*) FROM usuario_casos WHERE pode_gerenciar_compromissos = 1"
)[0][0]
if concedidos != 0:
    erros.append(
        f"0007 concedeu permissao automaticamente a {concedidos} linhas (esperado 0)"
    )
# a linha pre-existente (com pode_gerenciar_prazos=1) NAO herda a nova permissao
linha_uc = consulta(
    "SELECT pode_gerenciar_prazos, pode_gerenciar_compromissos FROM usuario_casos"
)
if linha_uc != [(1, 0)]:
    erros.append(f"estado da linha pre-0007 inesperado: {linha_uc!r}")

# BACKFILL seletivo: somente o numero CNJ-valido virou processo, ja normalizado
procs = consulta(
    "SELECT numero_processo, caso_id, tribunal, orgao_julgador, status, arquivado "
    "FROM processos_judiciais"
)
if len(procs) != 1:
    erros.append(f"backfill de processos inesperado ({len(procs)}): {procs!r}")
elif procs[0][0] != "00045678920238260050":
    erros.append(f"numero migrado nao normalizado: {procs[0][0]!r}")
elif procs[0][2] != "TJSP" or procs[0][3] != "1a Vara":
    erros.append(f"copia de tribunal/vara legados inesperada: {procs[0]!r}")

# o caso com numero INVALIDO nao virou processo e o legado permanece
invalidos = consulta(
    "SELECT COUNT(*) FROM processos_judiciais p "
    "JOIN casos c ON c.id = p.caso_id WHERE c.cliente = 'Cliente X'"
)[0][0]
if invalidos != 0:
    erros.append("numero legado invalido virou processo indevidamente")

# auditoria do backfill: CRIACAO marcada como migracao legada
hist_p3 = consulta("SELECT operacao, usuario_id, dados FROM processo_historicos")
if len(hist_p3) != 1 or hist_p3[0][0] != "CRIACAO" or "MIGRACAO_LEGADA" not in (hist_p3[0][2] or ""):
    erros.append(f"historico do backfill inesperado: {hist_p3!r}")

# legado de casos.numero_processo intacto (nada foi apagado nem reescrito)
legado_ok = consulta(
    "SELECT COUNT(*) FROM casos WHERE "
    "(cliente='Cliente X' AND numero_processo='1') OR "
    "(cliente='Cliente Valido' AND numero_processo='0004567-89.2023.8.26.0050')"
)[0][0]
if legado_ok != 2:
    erros.append("numeros legados de casos.numero_processo foram alterados")

# restricoes e indices
ddl_p3 = consulta(
    "SELECT sql FROM sqlite_master WHERE type='table' AND name='processos_judiciais'"
)[0][0]
if "uq_processos_numero" not in ddl_p3:
    erros.append("UNIQUE uq_processos_numero ausente")
if "ck_processos_valor_causa" not in ddl_p3:
    erros.append("CHECK ck_processos_valor_causa ausente")

fase3_idx = {
    "ix_processos_caso_id", "ix_processos_tribunal", "ix_processos_comarca",
    "ix_processos_instancia", "ix_processos_classe_processual", "ix_processos_status",
    "ix_processos_data_distribuicao", "ix_processos_arquivado",
    "ix_processo_historicos_processo_id",
}
if not fase3_idx <= idxs:
    erros.append(f"indices da Fase 3 ausentes: {fase3_idx - idxs}")

# UNIQUE e CHECK valem no banco (nao so no schema)
con = sqlite3.connect(db)
try:
    con.execute(
        "INSERT INTO processos_judiciais (caso_id, numero_processo, status, "
        "segredo_justica, arquivado, criado_em, atualizado_em) "
        "VALUES (1,'00045678920238260050','EM_ANDAMENTO',0,0,"
        "'2026-01-01 00:00:00','2026-01-01 00:00:00')"
    )
    con.commit()
    erros.append("UNIQUE de numero_processo nao impediu duplicata")
except sqlite3.IntegrityError:
    pass
try:
    con.execute(
        "INSERT INTO processos_judiciais (caso_id, numero_processo, status, "
        "segredo_justica, arquivado, valor_causa, criado_em, atualizado_em) "
        "VALUES (1,'00000013520268260100','EM_ANDAMENTO',0,0,-5,"
        "'2026-01-01 00:00:00','2026-01-01 00:00:00')"
    )
    con.commit()
    erros.append("CHECK de valor_causa nao impediu negativo")
except sqlite3.IntegrityError:
    pass
con.close()

# ------------------------------------------------------------ Fase 4 (0006)
if not {"compromissos", "compromisso_historicos", "prazo_historicos"} <= tabelas():
    erros.append("tabelas da Fase 4 ausentes apos upgrade")

cols_p4 = {r[1] for r in consulta("PRAGMA table_info(prazos)")}
fase4_cols = {
    "processo_id", "data_inicio", "data_vencimento", "status", "prioridade",
    "responsavel_id", "observacoes", "criado_por", "atualizado_em",
    "concluido_em", "concluido_por",
}
if not fase4_cols <= cols_p4:
    erros.append(f"colunas da Fase 4 ausentes: {fase4_cols - cols_p4}")
if {"data_limite", "cumprido"} & cols_p4:
    erros.append("colunas legadas de prazos nao removidas na 0006")

# BACKFILL reversivel: mesmos dados com os novos nomes/estados
linhas_p4 = consulta(
    "SELECT titulo, data_vencimento, status, responsavel_id, atualizado_em "
    "FROM prazos ORDER BY id"
)
esperado_p4 = [
    ("Prazo legado cumprido", "2026-11-20", "CONCLUIDO", 1, "2026-01-01 00:00:00"),
    ("Prazo legado aberto", "2026-12-01", "PENDENTE", 1, "2026-01-02 00:00:00"),
]
if linhas_p4 != esperado_p4:
    erros.append(f"backfill da 0006 inesperado: {linhas_p4!r}")

# auditoria do backfill: CRIACAO marcada como migracao legada
hist_p4 = consulta(
    "SELECT prazo_id, operacao, usuario_id, dados FROM prazo_historicos ORDER BY prazo_id"
)
if len(hist_p4) != 2 or any(
    h[1] != "CRIACAO" or "MIGRACAO_LEGADA" not in (h[3] or "") for h in hist_p4
):
    erros.append(f"historico do backfill de prazos inesperado: {hist_p4!r}")

# indices das consultas frequentes (e remocao dos legados)
idxs4 = {r[0] for r in consulta("SELECT name FROM sqlite_master WHERE type='index'")}
fase4_idx = {
    "ix_prazos_data_vencimento", "ix_prazos_status", "ix_prazos_prioridade",
    "ix_prazos_processo_id", "ix_prazos_responsavel_id", "ix_prazos_tipo",
    "ix_prazos_caso_id", "ix_compromissos_caso_id", "ix_compromissos_data_inicio",
    "ix_compromisso_historicos_compromisso_id", "ix_prazo_historicos_prazo_id",
}
if not fase4_idx <= idxs4:
    erros.append(f"indices da Fase 4 ausentes: {fase4_idx - idxs4}")
if {"ix_prazos_data_limite", "ix_prazos_cumprido"} & idxs4:
    erros.append("indices legados de prazos nao removidos")

# DDL: CHECK do periodo e FKs de compromissos
ddl_comp = consulta(
    "SELECT sql FROM sqlite_master WHERE type='table' AND name='compromissos'"
)[0][0]
if "ck_compromissos_periodo" not in ddl_comp:
    erros.append("CHECK ck_compromissos_periodo ausente")
if "REFERENCES casos" not in ddl_comp or "REFERENCES processos_judiciais" not in ddl_comp:
    erros.append("FKs de compromissos ausentes")


def _rejeita(sql: str) -> bool:
    # Executa SQL com foreign_keys=ON e reporta se o banco rejeitou.
    con = sqlite3.connect(db)
    con.isolation_level = None  # autocommit: pragma fora de transacao
    con.execute("PRAGMA foreign_keys = ON")
    try:
        con.execute(sql)
        return False
    except sqlite3.IntegrityError:
        return True
    finally:
        con.close()


# integridade: FKs e CHECK valem no banco (nao so no schema)
if not _rejeita(
    "INSERT INTO compromissos (caso_id, titulo, tipo, data_inicio, data_fim, "
    "status, criado_em, atualizado_em) VALUES (9999,'Orfa','AUDIENCIA',"
    "'2026-11-10 09:00:00','2026-11-10 10:00:00','AGENDADO',"
    "'2026-01-01 00:00:00','2026-01-01 00:00:00')"
):
    erros.append("FK de caso inexistente nao impediu compromisso")
if not _rejeita(
    "INSERT INTO compromissos (titulo, tipo, data_inicio, data_fim, status, "
    "criado_em, atualizado_em) VALUES ('Invertido','AUDIENCIA',"
    "'2026-11-10 10:00:00','2026-11-10 09:00:00','AGENDADO',"
    "'2026-01-01 00:00:00','2026-01-01 00:00:00')"
):
    erros.append("CHECK de periodo nao impediu data_fim <= data_inicio")
if not _rejeita(
    "INSERT INTO prazos (caso_id, processo_id, titulo, status, prioridade, "
    "data_vencimento, criado_em, atualizado_em) VALUES (1, 9999, 'Sem processo', "
    "'PENDENTE','MEDIA','2026-12-01',"
    "'2026-01-01 00:00:00','2026-01-01 00:00:00')"
):
    erros.append("FK de processo inexistente nao impediu prazo")

# nada do legado foi perdido
total_prazos = consulta("SELECT COUNT(*) FROM prazos")[0][0]
if total_prazos != 2:
    erros.append(f"prazos legados perdidos no upgrade: {total_prazos}")


# ---------------------------------------------------------------- downgrade
# primeiro reverte a Fase 4 (0006 -> 0005), depois a 3 (0005 -> 0004) e as
# Fases 1/2 (-> 0002)
command.downgrade(cfg, "0005_processos_judiciais")

# Fase 4 removida e legado reconstruido (data_limite/cumprido restaurados)
restantes4 = tabelas()
if {"compromissos", "compromisso_historicos", "prazo_historicos"} & restantes4:
    erros.append("tabelas da Fase 4 nao removidas no downgrade da 0006")
cols_p4d = {r[1] for r in consulta("PRAGMA table_info(prazos)")}
if fase4_cols & cols_p4d:
    erros.append(f"colunas da Fase 4 nao removidas: {fase4_cols & cols_p4d}")
if not {"data_limite", "cumprido"} <= cols_p4d:
    erros.append("colunas legadas nao restauradas no downgrade da 0006")
linhas_p4d = consulta("SELECT titulo, data_limite, cumprido FROM prazos ORDER BY id")
esperado_p4d = [
    ("Prazo legado cumprido", "2026-11-20", 1),
    ("Prazo legado aberto", "2026-12-01", 0),
]
if linhas_p4d != esperado_p4d:
    erros.append(f"restauracao legada inesperada: {linhas_p4d!r}")
idxs_p4d = {
    r[0]
    for r in consulta(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='prazos'"
    )
}
if not {"ix_prazos_caso_id", "ix_prazos_data_limite", "ix_prazos_cumprido"} <= idxs_p4d:
    erros.append(f"indices legados nao restaurados: {idxs_p4d}")

command.downgrade(cfg, "0004_casos_gestao")

restantes3 = tabelas()
if {"processos_judiciais", "processo_historicos"} & restantes3:
    erros.append("tabelas da Fase 3 nao removidas no downgrade da 0005")
cols_uc3d = {r[1] for r in consulta("PRAGMA table_info(usuario_casos)")}
if "pode_gerenciar_processos" in cols_uc3d:
    erros.append("pode_gerenciar_processos nao removida no downgrade da 0005")
if "pode_gerenciar_compromissos" in cols_uc3d:
    erros.append("pode_gerenciar_compromissos nao removida no downgrade da 0007")
# nada dos dados legados de casos foi afetado pela reversao da Fase 3
legado_pos_down = consulta("SELECT COUNT(*) FROM casos")[0][0]
if legado_pos_down != 4:
    erros.append(f"casos perdidos ao reverter a Fase 3: {legado_pos_down}")

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
if total_casos != 4:
    erros.append(f"casos perdidos durante a migracao: {total_casos}")

# ------------------------------------------------------------- re-upgrade
command.upgrade(cfg, "head")
if "clientes" not in tabelas():
    erros.append("re-upgrade falhou")
if not {"processos_judiciais", "processo_historicos"} <= tabelas():
    erros.append("re-upgrade da Fase 3 falhou")
# o backfill e repetivel: o mesmo numero valido vira processo de novo
procs_re = consulta("SELECT numero_processo FROM processos_judiciais")
if procs_re != [("00045678920238260050",)]:
    erros.append(f"backfill do re-upgrade inesperado: {procs_re!r}")

# re-upgrade da Fase 4: tabelas presentes e backfill de prazos repetivel
if not {"compromissos", "compromisso_historicos", "prazo_historicos"} <= tabelas():
    erros.append("re-upgrade da Fase 4 falhou (tabelas ausentes)")
linhas_re = consulta(
    "SELECT titulo, data_vencimento, status, responsavel_id FROM prazos ORDER BY id"
)
# responsavel_id e NULL: o downgrade ate 0002 remove casos.responsavel_id,
# entao no re-upgrade a coluna renasce vazia e o backfill herda NULL.
esperado_re = [
    ("Prazo legado cumprido", "2026-11-20", "CONCLUIDO", None),
    ("Prazo legado aberto", "2026-12-01", "PENDENTE", None),
]
if linhas_re != esperado_re:
    erros.append(f"backfill de prazos do re-upgrade inesperado: {linhas_re!r}")
# a auditoria do backfill nasce de novo com exatamente uma entrada por prazo
hist_re = consulta("SELECT COUNT(*) FROM prazo_historicos")[0][0]
if hist_re != 2:
    erros.append(f"historico do re-upgrade inesperado: {hist_re} entradas (esperado 2)")

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
