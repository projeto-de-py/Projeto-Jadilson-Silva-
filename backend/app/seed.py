"""Cria as tabelas (se ainda nao existirem) e o usuario Admin inicial.

Uso:
    python -m app.seed

Em producao prefira o Alembic:  alembic upgrade head
"""

import secrets
import sys

from sqlalchemy.exc import OperationalError

from app.core.security import hash_senha
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models.usuario import Perfil, Usuario
from app.repositories.usuario_repository import UsuarioRepository

ADMIN_NOME = "Jadilson Silva"
ADMIN_EMAIL = "admin@jadilson.adv"


def _erro_conexao(exc: OperationalError) -> None:
    """Mensagem amigavel quando o MySQL recusa a conexao (ex.: erro 1045)."""
    url = get_settings().database_url
    senha_info = "a senha configurada esta incorreta"
    if "1045" in str(exc):
        detalhe = "MySQL recusou o acesso: senha ou usuario invalidos (erro 1045)."
    elif "1049" in str(exc):
        detalhe = "Banco de dados inexistente (erro 1049)."
    elif "2003" in str(exc) or "Connection refused" in str(exc):
        detalhe = "MySQL nao esta rodando ou a porta esta errada (erro 2003)."
    else:
        detalhe = str(exc.orig) if getattr(exc, "orig", None) else str(exc)

    print("NAO FOI POSSIVEL CONECTAR AO BANCO DE DADOS")
    print(f"  Detalhe: {detalhe}")
    print(f"  URL usada: {url}")
    print("\nComo corrigir:")
    print("  1. Abra o arquivo .env (na pasta backend) e ajuste DATABASE_URL")
    print("     com o usuario/senha reais do seu MySQL, por exemplo:")
    print("     DATABASE_URL=mysql+pymysql://root:SUA_SENHA@localhost:3306/advocacia?charset=utf8mb4")
    print("  2. Se o arquivo .env nao existir, copie .env.example para .env")
    print("  3. Crie o banco uma unica vez:")
    print('     mysql -u root -p -e "CREATE DATABASE advocacia CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"')
    if "1045" in str(exc):
        print(f"  4. {senha_info} - confirme a senha do root no seu MySQL.")
    sys.exit(1)


def main() -> None:
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
    except OperationalError as exc:
        _erro_conexao(exc)

    db = SessionLocal()
    try:
        repo = UsuarioRepository(db)
        if repo.buscar_por_email(ADMIN_EMAIL):
            print(f"Admin ja cadastrado: {ADMIN_EMAIL}")
            return

        # Senha vem de ADMIN_SENHA_INICIAL no .env (dev) ou e gerada aleatoria
        # (recomendado) - nunca hardcoded no codigo.
        senha_inicial = (get_settings().admin_senha_inicial or "").strip()
        senha_gerada = not senha_inicial
        if senha_gerada:
            senha_inicial = secrets.token_urlsafe(15)  # ~90 bits de entropia

        repo.criar(
            Usuario(
                nome=ADMIN_NOME,
                email=ADMIN_EMAIL,
                senha_hash=hash_senha(senha_inicial),
                perfil=Perfil.ADMIN.value,
                ativo=True,
            )
        )
        print("Admin criado com sucesso:")
        print(f"  e-mail: {ADMIN_EMAIL}")
        print(f"  senha : {senha_inicial}")
        if senha_gerada:
            print("  -> Anote esta senha (gerada aleatoriamente).")
        print("  -> Troque a senha apos o primeiro login.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
