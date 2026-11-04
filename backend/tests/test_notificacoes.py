"""Testes de propriedade, deduplicação e marcos de notificação."""

from datetime import date, datetime, timedelta

from app.models.caso import Caso
from app.models.evento_agenda import EventoAgenda
from app.models.notificacao import Notificacao
from app.models.prazo import Prazo
from app.models.usuario_caso import UsuarioCaso
from app.repositories.notificacao_repository import NotificacaoRepository
from app.services.notificacao_service import (
    GeradorNotificacaoAudiencia,
    GeradorNotificacaoPrazo,
    GeradorNotificacaoRelatorioSemanal,
    NotificacaoService,
)
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


def test_audiencia_agendada_em_24h_gera_notificacao(db_session, admin):
    agora = datetime(2026, 11, 4, 10, 0)
    db_session.add(
        EventoAgenda(
            titulo="Audiência de Instrução",
            tipo="AUDIENCIA",
            inicio=agora + timedelta(hours=12),
            duracao=60,
            criado_por_id=admin.id,
        )
    )
    db_session.commit()

    repo = NotificacaoRepository(db_session)
    GeradorNotificacaoAudiencia(repo).gerar_para(admin, agora=agora)
    assert repo.contar_nao_lidas(admin.id) == 1


def test_relatorio_semanal_gera_na_sexta_feira(db_session, admin):
    sexta = date(2026, 11, 6)  # weekday() == 4
    repo = NotificacaoRepository(db_session)
    GeradorNotificacaoRelatorioSemanal(repo).gerar_para(admin, hoje=sexta)
    assert repo.contar_nao_lidas(admin.id) == 1


def test_endpoint_testar_e_limpar_notificacoes(client, admin, csrf_admin):
    resposta = client.post(
        "/api/notificacoes/testar",
        json={
            "tipos": [
                "prazoHoje",
                "prazo3dias",
                "audiencias",
                "novosClientes",
                "relatorioSemanal",
            ]
        },
        headers={"X-CSRF-Token": csrf_admin},
    )
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["criadas"] == 5
    assert len(corpo["itens"]) == 5

    limpar = client.post("/api/notificacoes/limpar", headers={"X-CSRF-Token": csrf_admin})
    assert limpar.status_code == 200
    assert limpar.json()["removidas"] == 5
    assert client.get("/api/notificacoes").json()["total"] == 0
    assert client.get("/api/notificacoes/nao-lidas/contagem").json()["nao_lidas"] == 0


def test_criar_evento_agenda_notifica_outro_usuario(client, admin, advogada, csrf_admin, db_session):
    inicio = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%dT14:00:00")
    # Cria evento atribuído à advogada
    resposta = client.post(
        "/api/agenda/eventos",
        json={
            "titulo": "Reunião de Alinhamento de Caso",
            "tipo": "REUNIAO",
            "inicio": inicio,
            "duracao": 60,
            "local": "Sala 1",
            "descricao": "Alinhamento com cliente",
            "destinatario_id": advogada.id,
        },
        headers={"X-CSRF-Token": csrf_admin},
    )
    assert resposta.status_code == 201

    repo = NotificacaoRepository(db_session)
    # A advogada deve ter recebido a notificação
    assert repo.contar_nao_lidas(advogada.id) == 1
    # O admin que criou não recebe auto-notificação
    assert repo.contar_nao_lidas(admin.id) == 0

    total, itens = repo.listar(advogada.id, pagina=1, limite=10, lidas=False)
    assert total == 1
    assert itens[0].tipo == "AGENDA_EVENTO"
    assert "Reunião de Alinhamento de Caso" in itens[0].mensagem

