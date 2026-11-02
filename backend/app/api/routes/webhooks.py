"""Webhooks do ZapSign e do Asaas.

Nao usam o cookie de sessao nem CSRF (quem chama e o provedor): cada um se
autentica por um segredo compartilhado, comparado em tempo constante. Sem o
segredo configurado, o endpoint FECHA (503) em vez de aceitar qualquer um.

Resposta: 200 quando o evento foi tratado, ignorado ou ja visto (o provedor nao
precisa reenviar); 503 quando a confirmacao no provedor falhou (ele reenvia).
"""

import json
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status as http_status

from app.api.routes.assinaturas import get_assinatura_service
from app.api.routes.financeiro import get_financeiro_service
from app.config import get_settings
from app.services.assinatura_service import AssinaturaService
from app.services.financeiro_service import FinanceiroService
from app.integrations.erros import IntegracaoErro

router = APIRouter()
log = logging.getLogger("webhooks")

MAX_CORPO = 1_000_000  # 1 MB


def _segredo_confere(informado: str | None, esperado: str | None) -> bool:
    if not esperado or not informado:
        return False
    return secrets.compare_digest(informado.encode(), esperado.encode())


async def _ler_json(request: Request) -> dict:
    corpo = await request.body()
    if len(corpo) > MAX_CORPO:
        raise HTTPException(http_status.HTTP_413_CONTENT_TOO_LARGE, "Corpo grande demais.")
    try:
        dados = json.loads(corpo or b"{}")
    except ValueError:
        raise HTTPException(http_status.HTTP_400_BAD_REQUEST, "JSON invalido.")
    if not isinstance(dados, dict):
        raise HTTPException(http_status.HTTP_400_BAD_REQUEST, "Payload invalido.")
    return dados


@router.post("/zapsign", summary="Webhook do ZapSign (autenticado por segredo)")
async def webhook_zapsign(
    request: Request, servico: AssinaturaService = Depends(get_assinatura_service)
) -> dict:
    s = get_settings()
    esperado = s.zapsign_webhook_secret.get_secret_value() if s.zapsign_webhook_secret else None
    if esperado is None:
        raise HTTPException(http_status.HTTP_503_SERVICE_UNAVAILABLE, "Webhook nao configurado.")
    if not _segredo_confere(request.headers.get(s.zapsign_webhook_header), esperado):
        raise HTTPException(http_status.HTTP_401_UNAUTHORIZED, "Nao autorizado.")
    payload = await _ler_json(request)
    try:
        resultado = servico.processar_webhook(payload)
    except IntegracaoErro as exc:
        log.warning("zapsign webhook: falha ao confirmar (%s)", exc.mensagem)
        raise HTTPException(http_status.HTTP_503_SERVICE_UNAVAILABLE, "Nao foi possivel confirmar agora.")
    log.info("zapsign webhook: %s", resultado)
    return {"status": resultado}


@router.post("/asaas", summary="Webhook do Asaas (autenticado por token)")
async def webhook_asaas(
    request: Request, servico: FinanceiroService = Depends(get_financeiro_service)
) -> dict:
    s = get_settings()
    esperado = s.asaas_webhook_token.get_secret_value() if s.asaas_webhook_token else None
    if esperado is None:
        raise HTTPException(http_status.HTTP_503_SERVICE_UNAVAILABLE, "Webhook nao configurado.")
    if not _segredo_confere(request.headers.get("asaas-access-token"), esperado):
        raise HTTPException(http_status.HTTP_401_UNAUTHORIZED, "Nao autorizado.")
    payload = await _ler_json(request)
    try:
        resultado = servico.processar_webhook(payload)
    except IntegracaoErro as exc:
        log.warning("asaas webhook: falha ao confirmar (%s)", exc.mensagem)
        raise HTTPException(http_status.HTTP_503_SERVICE_UNAVAILABLE, "Nao foi possivel confirmar agora.")
    log.info("asaas webhook: %s", resultado)
    return {"status": resultado}
