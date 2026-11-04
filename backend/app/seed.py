"""Cria as tabelas (se ainda nao existirem) e o usuario Admin inicial.

Uso:
    python -m app.seed

Em producao prefira o Alembic:  alembic upgrade head
"""

import secrets
import sys
from datetime import date, timedelta

from sqlalchemy.exc import OperationalError

from app.core.security import hash_senha
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models import Caso, Prazo
from app.models.usuario import Perfil, Usuario
from app.repositories.usuario_repository import UsuarioRepository

ADMIN_NOME = "Jadilson Silva"
ADMIN_EMAIL = "admin@jadilson.adv"

CASOS_DEMO = [
    ("0001234-56.2025.8.26.0100", "Mariana Costa", "Banco Aurora", "Civel", "EM_ANDAMENTO"),
    ("0002345-67.2024.5.03.0021", "Rafael Almeida", "INSS", "Previdenciario", "EM_ANDAMENTO"),
    ("0003456-78.2025.8.19.0001", "Comercial Horizonte Ltda.", "Distribuidora Sul", "Empresarial", "EM_ANDAMENTO"),
    ("0004567-89.2023.8.26.0050", "Paula Nascimento", "Condominio Parque Azul", "Civel", "AGUARDANDO_SENTENCA"),
    ("0005678-90.2025.8.15.2001", "Joao Pedro Santos", "Seguradora Nacional", "Consumidor", "EM_ANDAMENTO"),
    ("0006789-01.2022.8.26.0562", "Helena Ribeiro", "Construtora Vale", "Trabalhista", "SUSPENSO"),
]


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

    config = get_settings()
    # Conta do advogado principal vem da configuracao administrativa (.env) -
    # e o unico lugar onde nasce a permissao `administrador`.
    admin_email = (config.admin_email or ADMIN_EMAIL).strip().lower()

    db = SessionLocal()
    try:
        repo = UsuarioRepository(db)
        existente = repo.buscar_por_email(admin_email)
        if existente:
            print(f"Admin ja cadastrado: {admin_email}")
            if not existente.administrador:
                # bancos criados antes da Fase 1: assegura a permissao na conta
                existente.administrador = True
                db.commit()
                print("  -> permissao administrativa assegurada nesta conta.")
        else:
            # Senha vem do .env ou e gerada aleatoriamente; nunca hardcoded.
            senha_inicial = (config.admin_senha_inicial or "").strip()
            senha_gerada = not senha_inicial
            if senha_gerada:
                senha_inicial = secrets.token_urlsafe(15)
            repo.criar(
                Usuario(nome=ADMIN_NOME, email=admin_email,
                        senha_hash=hash_senha(senha_inicial),
                        perfil=Perfil.ADVOGADO.value, administrador=True, ativo=True)
            )
            print("Admin criado com sucesso (advogado principal):")
            print(f"  e-mail: {admin_email}")
            print(f"  senha : {senha_inicial}")
            if senha_gerada:
                print("  -> Anote esta senha (gerada aleatoriamente).")
            print("  -> Troque a senha apos o primeiro login.")
        # Dados demonstrativos ficticios, inseridos uma unica vez por numero CNJ.
        casos = {}
        for numero, cliente, parte, area, estado in CASOS_DEMO:
            caso = db.query(Caso).filter_by(numero_processo=numero).one_or_none()
            if caso is None:
                caso = Caso(numero_processo=numero, cliente=cliente, parte_contraria=parte,
                            area=area, status=estado, tribunal="Tribunal de Justiça (fictício)")
                db.add(caso)
            casos[numero] = caso
        db.flush()
        amostras = [
            (0, "Revisar documentos para manifestação", 2),
            (1, "Apresentar réplica", 4),
            (2, "Audiência de conciliação", 9),
            (4, "Juntar comprovantes", 15),
        ]
        for indice, titulo, dias in amostras:
            numero = CASOS_DEMO[indice][0]
            caso = casos[numero]
            prazo_existente = db.query(Prazo).filter_by(caso_id=caso.id, titulo=titulo).one_or_none()
            if prazo_existente is None:
                db.add(Prazo(caso_id=casos[numero].id, titulo=titulo, tipo="PROCESSUAL",
                             data_limite=date.today() + timedelta(days=dias),
                             descricao="Prazo demonstrativo fictício."))
        db.commit()
        print("Dados demonstrativos assegurados: 6 processos e 4 prazos ficticios.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
