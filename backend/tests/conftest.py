"""Fixtures compartilhadas dos testes.

Usam SQLite em memoria (substituindo o MySQL) injetando uma sessao via
dependency override do FastAPI - nenhum teste toca no banco real.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_senha
from app.database import Base, get_db
from app.main import create_app
from app.models.usuario import Perfil, Usuario

ADMIN = {
    "nome": "Jadilson Silva",
    "email": "admin@jadilson.adv",
    "senha": "Admin@123",
    "perfil": Perfil.ADMIN.value,
}
PADRAO = {
    "nome": "Ana Advogada",
    "email": "ana@jadilson.adv",
    "senha": "Ana@1234",
    "perfil": Perfil.PADRAO.value,
}


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # todas as sessoes compartilham a mesma conexao
    )
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def db_session(engine):
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False
    )
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture()
def app(db_session):
    aplicacao = create_app()

    def override_get_db():
        yield db_session

    aplicacao.dependency_overrides[get_db] = override_get_db
    return aplicacao


@pytest.fixture()
def client(app):
    app.state.limiter.reset()  # isola o rate limit entre testes
    with TestClient(app) as c:
        yield c
    app.state.limiter.reset()


def _criar_usuario(db, dados: dict) -> Usuario:
    usuario = Usuario(
        nome=dados["nome"],
        email=dados["email"],
        senha_hash=hash_senha(dados["senha"]),
        perfil=dados["perfil"],
        ativo=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@pytest.fixture()
def admin(db_session) -> Usuario:
    return _criar_usuario(db_session, ADMIN)


@pytest.fixture()
def advogada(db_session) -> Usuario:
    return _criar_usuario(db_session, PADRAO)


@pytest.fixture()
def fazer_login(client):
    """Autentica e devolve a resposta do login (com cookie + csrf_token)."""

    def _login(email: str, senha: str) -> dict:
        resp = client.post(
            "/api/auth/login", json={"email": email, "senha": senha}
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    return _login


@pytest.fixture()
def csrf_admin(fazer_login, admin) -> str:
    """CSRF de um login valido como Admin (cookie ja fica no client)."""
    return fazer_login(ADMIN["email"], ADMIN["senha"])["csrf_token"]
