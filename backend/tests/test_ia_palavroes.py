"""Palavrao e giria de palavrao: o pedido e recusado, o texto vira aviso critico de tom."""

import pytest

from app.ia import revisor
from app.ia.guardrails import entrada as g_in
from tests.conftest import PADRAO

CSRF = "X-CSRF-Token"


@pytest.mark.parametrize("texto", [
    "essa porra de processo",
    "que merda de juiz",
    "escreve essa bosta",
    "vai se foder",
    "p0rra, escreve logo",
    "caralhooo que demora",
    "c4ralho",
    "krl mano",
    "o fdp do banco",
    "vsf e redige isso",
    "PQP",
    "p.o.r.r.a",
    "filho da puta",
    "esse cuzao",
])
def test_detecta_palavrao_e_giria(texto):
    assert g_in.detectar_palavrao(texto), texto


@pytest.mark.parametrize("texto", [
    "A parte autora requer a procedência dos pedidos.",
    "O réu agiu de má-fé, conforme o art. 80 do CPC.",
    "Computação, putativo e disputa não são palavrões.",
    "Cláusula 4ª do contrato nº 12345",
])
def test_texto_formal_nao_e_palavrao(texto):
    assert not g_in.detectar_palavrao(texto), texto


def test_pedido_com_palavrao_e_bloqueado():
    r = g_in.analisar_entrada("escreve logo essa porra de contestação")
    assert r.bloqueado and "palavrões" in r.motivo


def test_revisor_marca_palavrao_como_critico():
    achados = revisor.analisar("O banco é uma merda e o gerente é um fdp, requer a procedência.")
    tom = [s for s in achados if s.categoria == "tom" and "Palavrões" in s.titulo]
    assert tom and tom[0].severidade == "critica"


def test_api_recusa_pedido_com_palavrao(client, csrf_de):
    csrf = csrf_de(PADRAO)
    resp = client.post(
        "/api/ia/sugerir",
        headers={CSRF: csrf},
        json={"tarefa": "continuar", "pedido": "escreve essa porra logo, krl", "texto_documento": "x" * 30},
    )
    assert resp.status_code == 422
    assert "palavrões" in resp.json()["detail"]


def test_api_nao_autocompleta_em_cima_de_palavrao(client, csrf_de):
    csrf = csrf_de(PADRAO)
    corpo = client.post("/api/ia/completar", headers={CSRF: csrf}, json={"texto_antes": "que merda, a autora pede a justiça gratuita"}).json()
    assert corpo["continuacao"] is None
