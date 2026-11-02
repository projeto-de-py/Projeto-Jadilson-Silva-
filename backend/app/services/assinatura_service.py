"""Regras da assinatura eletronica: enviar o PDF ao ZapSign e acompanhar o status."""

import base64
import binascii
import hashlib
from datetime import datetime, timezone

from app.config import get_settings
from app.models.caso import Caso
from app.models.assinatura import (
    ST_ASSINADO,
    ST_ENVIADO,
    ST_RECUSADO,
    Assinatura,
)
from app.models.usuario import Usuario
from app.repositories.assinatura_repository import AssinaturaRepository
from app.repositories.caso_repository import CasoRepository
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.evento_webhook_repository import EventoWebhookRepository
from app.schemas.assinatura import AssinaturaCreate
from app.services.zapsign import ZapSignService

MAX_PDF_BYTES = 10 * 1024 * 1024


class AssinaturaDadosInvalidosError(Exception):
    """Dado de entrada invalido (vira 422)."""


class RegistroNaoEncontradoError(Exception):
    """Cliente ou caso inexistente (vira 404)."""


def validar_pdf(pdf_base64: str) -> tuple[str, bytes]:
    """Decodifica o base64 e confere que e mesmo um PDF dentro do limite."""
    limpo = "".join(pdf_base64.split())
    if limpo.startswith("data:"):
        limpo = limpo.split(",", 1)[-1]
    try:
        bruto = base64.b64decode(limpo, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise AssinaturaDadosInvalidosError("O PDF enviado nao esta em base64 valido.") from exc
    if not bruto.startswith(b"%PDF-"):
        raise AssinaturaDadosInvalidosError("O arquivo enviado nao e um PDF.")
    if len(bruto) > MAX_PDF_BYTES:
        raise AssinaturaDadosInvalidosError("O PDF excede o limite de 10 MB.")
    return limpo, bruto


class AssinaturaService:
    def __init__(
        self,
        assinaturas: AssinaturaRepository,
        clientes: ClienteRepository,
        casos: CasoRepository,
        eventos: EventoWebhookRepository,
        zapsign: ZapSignService,
    ):
        self.assinaturas = assinaturas
        self.clientes = clientes
        self.casos = casos
        self.eventos = eventos
        self.zapsign = zapsign

    # ------------------------------------------------------------------ envio

    def enviar(self, dados: AssinaturaCreate, operador: Usuario) -> Assinatura:
        cliente = self.clientes.buscar_por_id(dados.cliente_id)
        if cliente is None or not cliente.ativo:
            raise RegistroNaoEncontradoError("Cliente nao encontrado")
        if dados.caso_id is not None and self.casos.db.get(Caso, dados.caso_id) is None:
            raise RegistroNaoEncontradoError("Caso nao encontrado")
        if not cliente.email and not cliente.telefone:
            raise AssinaturaDadosInvalidosError(
                "O cliente precisa ter e-mail ou WhatsApp cadastrado para receber o documento."
            )

        pdf_b64, pdf_bytes = validar_pdf(dados.pdf_base64)
        resposta = self.zapsign.criar_documento(
            nome=dados.titulo,
            pdf_base64=pdf_b64,
            signatario_nome=cliente.nome,
            signatario_email=cliente.email,
            signatario_telefone=cliente.telefone,
            mensagem=dados.mensagem,
        )
        return self.assinaturas.criar(
            cliente_id=cliente.id,
            caso_id=dados.caso_id,
            titulo=dados.titulo,
            zapsign_doc_token=resposta["token"],
            link_assinatura=resposta.get("link"),
            status=ST_ENVIADO,
            signatario_nome=cliente.nome,
            signatario_email=cliente.email,
            pdf_sha256=hashlib.sha256(pdf_bytes).hexdigest(),
            criado_por=operador.id,
        )

    # ---------------------------------------------------------------- webhook

    def processar_webhook(self, payload: dict) -> str:
        """Atualiza o status quando o ZapSign avisa. Devolve o que aconteceu (para o log)."""
        doc = payload.get("doc") if isinstance(payload.get("doc"), dict) else {}
        token = payload.get("token") or doc.get("token")
        if not isinstance(token, str) or not token:
            return "ignorado: sem token"
        tipo = str(payload.get("event_type") or "")
        status_payload = str(payload.get("status") or doc.get("status") or "")

        assinatura = self.assinaturas.buscar_por_token(token)
        if assinatura is None:
            return "ignorado: documento desconhecido"

        status_real = status_payload
        if get_settings().webhooks_verificar_na_api:
            # Nao confia so no aviso: pergunta ao ZapSign como o documento esta de verdade.
            status_real = str(self.zapsign.consultar_documento(token).get("status") or "")

        novo = _mapear_status(status_real)
        if novo is None:
            return f"ignorado: status {status_real or '?'}"

        if not self.eventos.registrar("zapsign", f"{token}:{tipo}:{status_real}", tipo or status_real):
            return "duplicado"
        if assinatura.status == ST_ASSINADO:
            self.assinaturas.db.commit()
            return "ja assinado"  # nunca volta de ASSINADO
        assinatura.status = novo
        if novo == ST_ASSINADO:
            assinatura.assinado_em = datetime.now(timezone.utc).replace(tzinfo=None)
        self.assinaturas.salvar(assinatura)
        return f"status={novo}"


def _mapear_status(status: str) -> str | None:
    s = status.strip().lower()
    if s in ("signed", "assinado"):
        return ST_ASSINADO
    if s in ("refused", "rejected", "recusado"):
        return ST_RECUSADO
    return None
