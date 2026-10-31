"""Fixtures compartilhadas dos testes.

Usam SQLite em memoria (substituindo o MySQL) injetando uma sessao via
dependency override do FastAPI - nenhum teste toca no banco real.
"""

import itertools

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_senha
from app.database import Base, get_db
from app.main import create_app
from app.models.caso import Caso
from app.models.cliente import Cliente
from app.models.usuario import Perfil, Usuario
from app.models.usuario_caso import UsuarioCaso

# Advogado principal (provisionado com a permissao administrativa)
ADMIN = {
    "nome": "Jadilson Silva",
    "email": "admin@jadilson.adv",
    "senha": "Admin@123",
    "perfil": Perfil.ADVOGADO.value,
    "administrador": True,
}
# Advogado colaborador (sem privilegios administrativos)
PADRAO = {
    "nome": "Ana Advogada",
    "email": "ana@jadilson.adv",
    "senha": "Ana@1234",
    "perfil": Perfil.ADVOGADO.value,
    "administrador": False,
}
# Funcionario (sem privilegios administrativos)
FUNCIONARIO = {
    "nome": "Felipe Funcionario",
    "email": "felipe@jadilson.adv",
    "senha": "Felipe@123",
    "perfil": Perfil.FUNCIONARIO.value,
    "administrador": False,
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
        administrador=dados.get("administrador", False),
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
def funcionario(db_session) -> Usuario:
    return _criar_usuario(db_session, FUNCIONARIO)


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
def csrf_de(client, fazer_login, admin, advogada, funcionario):
    """Loga com as constantes de usuario (ADMIN/PADRAO/FUNCIONARIO) e devolve o CSRF.

    Depende das fixtures de usuario para garantir que a conta exista no banco
    antes do login (mesmo quando o teste so usa uma delas).
    """

    def _csrf(dados: dict) -> str:
        return fazer_login(dados["email"], dados["senha"])["csrf_token"]

    return _csrf


@pytest.fixture()
def csrf_admin(fazer_login, admin) -> str:
    """CSRF de um login valido como Admin (cookie ja fica no client)."""
    return fazer_login(ADMIN["email"], ADMIN["senha"])["csrf_token"]


# ------------------------------------------------- massa de casos/clientes


@pytest.fixture()
def criar_caso(db_session):
    """Cria casos com numero CNJ unico (um banco novo por teste)."""
    contador = itertools.count(1)

    def _criar(cliente: str = "Cliente Teste", **kwargs) -> Caso:
        n = next(contador)
        kwargs.setdefault("numero_processo", f"{n:07d}-00.2026.8.26.0100")
        caso = Caso(cliente=cliente, **kwargs)
        db_session.add(caso)
        db_session.commit()
        db_session.refresh(caso)
        return caso

    return _criar


@pytest.fixture()
def criar_cliente(db_session):
    contador = itertools.count(1)

    def _criar(nome: str | None = None, **kwargs) -> Cliente:
        n = next(contador)
        cliente = Cliente(nome=nome or f"Cliente {n}", **kwargs)
        db_session.add(cliente)
        db_session.commit()
        db_session.refresh(cliente)
        return cliente

    return _criar


@pytest.fixture()
def conceder_acesso(db_session, admin):
    """Concede acesso direto no banco (setup de testes de leitura)."""

    def _conceder(caso: Caso, usuario: Usuario, **kwargs) -> UsuarioCaso:
        linha = UsuarioCaso(
            caso_id=caso.id,
            usuario_id=usuario.id,
            concedido_por=admin.id,
            **kwargs,
        )
        db_session.add(linha)
        db_session.commit()
        db_session.refresh(linha)
        return linha

    return _conceder
