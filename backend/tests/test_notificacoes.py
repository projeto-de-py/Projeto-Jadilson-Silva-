"""Testes de propriedade, deduplicação e marcos de notificação."""

from datetime import date, timedelta

from app.models.caso import Caso
from app.models.notificacao import Notificacao
from app.models.prazo import Prazo
from app.models.usuario_caso import UsuarioCaso
from app.repositories.notificacao_repository import NotificacaoRepository
from app.services.notificacao_service import GeradorNotificacaoPrazo, NotificacaoService
from tests.conftest import PADRAO


def _criar_aviso(db, usuario_id: int, chave: str) -> Notificacao:
    return Notificacao(
        usuario_id=usuario_id,
        tipo="TESTE",
        titulo="Aviso de teste",
        mensagem="Mensagem sem dados sensíveis.",
        link="/home",
        severidade="info",
        chave_dedupe=chave,
    )


def test_dedupe_por_usuario(client, db_session, admin, csrf_admin):
    servico = NotificacaoService(NotificacaoRepository(db_session))
    dados = dict(usuario_id=admin.id, tipo="TESTE", titulo="Teste", mensagem="Mensagem", link="/home", severidade="info", chave_dedupe="mesma-chave")
    assert servico.criar(**dados) is not None
    assert servico.criar(**dados) is None
    resposta = client.get("/api/notificacoes")
    assert resposta.status_code == 200
    assert resposta.json()["total"] == 1


def test_usuario_nao_le_ou_marca_aviso_de_outro(client, db_session, admin, advogada, fazer_login):
    aviso = _criar_aviso(db_session, admin.id, "privado-admin")
    db_session.add(aviso)
    db_session.commit()
    csrf = fazer_login(PADRAO["email"], PADRAO["senha"])["csrf_token"]
    assert client.get("/api/notificacoes").json()["itens"] == []
    assert client.post(f"/api/notificacoes/{aviso.id}/lida", headers={"X-CSRF-Token": csrf}).status_code == 404


def test_escrita_exige_csrf(client, csrf_admin):
    assert client.post("/api/notificacoes/lidas").status_code == 403


def test_prazo_notifica_apenas_usuario_com_acesso(db_session, admin, advogada):
    caso = Caso(cliente="Cliente de teste", criado_por=admin.id)
    db_session.add(caso)
    db_session.flush()
    db_session.add(Prazo(caso_id=caso.id, titulo="Prazo interno", data_limite=date.today() + timedelta(days=3)))
    db_session.add(UsuarioCaso(usuario_id=advogada.id, caso_id=caso.id, pode_visualizar=True, ativo=True, concedido_por=admin.id))
    db_session.commit()

    repo = NotificacaoRepository(db_session)
    GeradorNotificacaoPrazo(repo).gerar_para(advogada)
    assert repo.contar_nao_lidas(advogada.id) == 1
    assert repo.contar_nao_lidas(admin.id) == 0
