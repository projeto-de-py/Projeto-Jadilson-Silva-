"""Smoke do fluxo completo contra o MySQL real (fora da suíte pytest).

Uso (dentro de `backend/`, com a API já rodando):

    $env:ADMIN_SENHA = "<senha local do seed>"
    .\\.venv\\Scripts\\python.exe -m scripts.smoke_mysql

O script usa dados com prefixo `Smoke <timestamp>` e, por padrão, **apaga o
que criou** no final (use `--manter` para conservar a massa de demonstração).
Nunca grava senha em arquivo: se `ADMIN_SENHA` não estiver exportada, o script
monta um JWT de smoke com o `JWT_SECRET` do `.env` local (não versionado) e o
administrador ativo do banco. O login por senha continua sendo usado quando a
credencial está disponível.
"""

from __future__ import annotations

import argparse
import os
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx
from dotenv import dotenv_values
from sqlalchemy import text

from app.database import SessionLocal
from app.repositories.notificacao_repository import NotificacaoRepository


def _credenciais() -> tuple[str, str | None]:
    env = dotenv_values(Path.cwd() / ".env")
    senha = os.environ.get("ADMIN_SENHA") or env.get("ADMIN_SENHA_INICIAL")
    return env.get("ADMIN_EMAIL", "admin@jadilson.adv"), str(senha) if senha else None


def _sessao_local() -> tuple[dict[str, str], int, str, str]:
    """Sessão de smoke sem senha, usando apenas o `.env` e o banco locais."""
    from app.config import get_settings
    from app.core import security
    from app.models.usuario import Usuario

    settings = get_settings()
    db = SessionLocal()
    try:
        admin = db.query(Usuario).filter(
            Usuario.administrador.is_(True), Usuario.ativo.is_(True)
        ).first()
        if admin is None:
            raise SystemExit("Nenhum administrador ativo encontrado no banco local")
        csrf = "smoke-local"
        token = security.criar_token(str(admin.id), admin.perfil, csrf)
        headers = {
            "X-CSRF-Token": csrf,
            "Cookie": f"{settings.auth_cookie_name}={token}",
        }
        return headers, admin.id, settings.auth_cookie_name, token
    finally:
        db.close()


def _cnj_valido(sequencia: int) -> str:
    """Gera um CNJ válido (módulo 97) sem depender das fixtures de teste."""
    prefixo = f"{sequencia:07d}"
    for digito in range(100):
        candidato = f"{prefixo}{digito:02d}20268260100"
        if int(candidato) % 97 == 1:
            return f"{prefixo}-{digito:02d}.2026.8.26.0100"
    raise RuntimeError(f"não foi possível gerar CNJ válido para {prefixo}")


def _limpar(
    cliente_id: int,
    caso_id: int,
    processo_id: int,
    prazo_id: int,
    documento_id: int,
) -> None:
    """Remove apenas os registros criados por esta execução, em ordem de FK."""
    db = SessionLocal()
    try:
        db.execute(
            text("DELETE FROM notificacoes WHERE chave_dedupe LIKE :chave"),
            {"chave": f"prazo:{prazo_id}:%"},
        )
        db.execute(
            text("DELETE FROM notificacoes WHERE chave_dedupe LIKE :chave"),
            {"chave": f"cliente:{cliente_id}:%"},
        )
        db.execute(
            text("DELETE FROM prazo_historicos WHERE prazo_id = :id"), {"id": prazo_id}
        )
        db.execute(
            text("DELETE FROM processo_historicos WHERE processo_id = :id"),
            {"id": processo_id},
        )
        db.execute(
            text("DELETE FROM processos_judiciais WHERE id = :id"), {"id": processo_id}
        )
        db.execute(text("DELETE FROM prazos WHERE id = :id"), {"id": prazo_id})
        db.execute(
            text("DELETE FROM andamentos WHERE caso_id = :id"), {"id": caso_id}
        )
        db.execute(text("DELETE FROM documentos WHERE id = :id"), {"id": documento_id})
        db.execute(text("DELETE FROM casos WHERE id = :id"), {"id": caso_id})
        db.execute(text("DELETE FROM clientes WHERE id = :id"), {"id": cliente_id})
        db.commit()
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--manter", action="store_true", help="não apagar os dados criados")
    args = parser.parse_args()

    email, senha = _credenciais()
    sufixo = datetime.now().strftime("%Y%m%d%H%M%S%f")[:17]
    prefixo = f"Smoke {sufixo}"
    cliente_id = caso_id = processo_id = prazo_id = documento_id = 0

    try:
        with httpx.Client(base_url=f"{args.base_url}/api", timeout=30) as api:
            saude = api.get(f"{args.base_url}/health")
            assert saude.status_code == 200 and saude.json()["status"] == "ok", saude.text

            if senha:
                login = api.post("/auth/login", json={"email": email, "senha": senha})
                assert login.status_code == 200, login.text
                headers = {"X-CSRF-Token": login.json()["csrf_token"]}
                usuario_id = login.json()["usuario"]["id"]
            else:
                headers, usuario_id, cookie_name, token = _sessao_local()
                api.cookies.set(cookie_name, token, domain="127.0.0.1", path="/")
                print("ADMIN_SENHA não exportada: usando JWT local de smoke.")

            cliente = api.post(
                "/clientes", json={"nome": f"Cliente {prefixo}"}, headers=headers
            )
            assert cliente.status_code == 201, cliente.text
            cliente_id = cliente.json()["id"]

            caso = api.post(
                "/casos",
                json={
                    "titulo": f"Caso {prefixo}",
                    "cliente_id": cliente_id,
                    "area": "PREVIDENCIARIO",
                },
                headers=headers,
            )
            assert caso.status_code == 201, caso.text
            caso_id = caso.json()["id"]

            numero_cnj = _cnj_valido(int(sufixo[-7:]))
            processo = api.post(
                f"/casos/{caso_id}/processos",
                json={"numero_processo": numero_cnj},
                headers=headers,
            )
            assert processo.status_code == 201, processo.text
            processo_id = processo.json()["id"]

            consulta_processo = api.get(
                "/processos", params={"q": numero_cnj.replace("-", "")[:7]}
            )
            assert consulta_processo.status_code == 200, consulta_processo.text
            assert consulta_processo.json()["total"] == 1

            vencimento = date.today() + timedelta(days=1)
            prazo = api.post(
                "/prazos",
                json={
                    "caso_id": caso_id,
                    "titulo": f"Prazo {prefixo}",
                    "data_vencimento": vencimento.isoformat(),
                    "prioridade": "ALTA",
                },
                headers=headers,
            )
            assert prazo.status_code == 201, prazo.text
            prazo_id = prazo.json()["id"]

            andamento = api.post(
                f"/casos/{caso_id}/andamentos",
                json={"titulo": f"Andamento {prefixo}", "descricao": "smoke"},
                headers=headers,
            )
            assert andamento.status_code == 201, andamento.text

            documento = api.post(
                "/documentos",
                json={
                    "titulo": f"Documento {prefixo}",
                    "caso_id": caso_id,
                    "html": "<p>smoke</p>",
                },
                headers=headers,
            )
            assert documento.status_code == 201, documento.text
            documento_id = documento.json()["id"]

            # Filtros RF09 rodam no banco, não no recorte já carregado na tela.
            for rota in ("clientes", "casos", "prazos"):
                resposta = api.get(f"/{rota}", params={"q": prefixo})
                assert resposta.status_code == 200, (rota, resposta.text)
                assert resposta.json()["total"] == 1, (rota, resposta.json()["total"])

            lista = api.get("/documentos", params={"limite": 200})
            assert lista.status_code == 200, lista.text
            assert any(d["id"] == documento_id for d in lista.json()["itens"])

        # Aviso gravado no evento de escrita, antes de consultar notificações.
        db = SessionLocal()
        try:
            aviso = NotificacaoRepository(db).buscar_dedupe(
                usuario_id, f"prazo:{prazo_id}:{vencimento.isoformat()}:marco-1"
            )
        finally:
            db.close()
        assert aviso is not None, "aviso do prazo não foi gravado pelo evento"

        print(
            f"OK: cliente={cliente_id} caso={caso_id} processo={processo_id} "
            f"prazo={prazo_id} andamento={andamento.json()['id']} "
            f"documento={documento_id} aviso={aviso.id}; filtros no banco conferidos"
        )
    finally:
        if cliente_id and not args.manter:
            _limpar(cliente_id, caso_id, processo_id, prazo_id, documento_id)
            print("Dados do smoke removidos (use --manter para conservá-los).")


if __name__ == "__main__":
    main()
