"""Regras da assinatura eletronica: enviar o PDF ao provedor (Autentique/ZapSign) e acompanhar o status."""

import base64
import binascii
import hashlib
from datetime import datetime, timezone

from app.config import get_settings
from app.models.assinatura import (
    ST_ASSINADO,
    ST_ENVIADO,
    ST_RECUSADO,
    Assinatura,
)
from app.models.caso import Caso
from app.models.usuario import Usuario
from app.repositories.assinatura_repository import AssinaturaRepository
from app.repositories.caso_repository import CasoRepository
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.evento_webhook_repository import EventoWebhookRepository
from app.repositories.notificacao_repository import NotificacaoRepository
from app.schemas.assinatura import AssinaturaCreate
from app.services.notificacao_service import (
    GeradorNotificacaoFinanceira,
    NotificacaoService,
)
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
        raise AssinaturaDadosInvalidosError(
            "O PDF enviado nao esta em base64 valido."
        ) from exc
    if not bruto.startswith(b"%PDF-"):
        raise AssinaturaDadosInvalidosError("O arquivo enviado nao e um PDF.")
    if len(bruto) > MAX_PDF_BYTES:
        raise AssinaturaDadosInvalidosError("O PDF excede o limite de 10 MB.")
    return limpo, bruto


def _extrair_dados_webhook(payload: dict) -> tuple[str | None, str, str]:
    """Extrai (token, tipo_evento, status) tanto de payloads Autentique quanto ZapSign."""
    doc = payload.get("doc") if isinstance(payload.get("doc"), dict) else {}
    evento_aut = (
        payload.get("event") if isinstance(payload.get("event"), dict) else {}
    )
    dados_aut = (
        evento_aut.get("data")
        if isinstance(evento_aut.get("data"), dict)
        else {}
    )
    obj_aut = (
        dados_aut.get("object")
        if isinstance(dados_aut.get("object"), dict)
        else dados_aut
    )
    doc_aut = (
        payload.get("documento")
        if isinstance(payload.get("documento"), dict)
        else {}
    )

    token = (
        payload.get("token")
        or doc.get("token")
        or obj_aut.get("document")
        or obj_aut.get("id")
        or doc_aut.get("uuid")
        or doc_aut.get("id")
    )
    tipo = str(
        payload.get("event_type")
        or evento_aut.get("type")
        or payload.get("evento")
        or ""
    )
    status_payload = str(
        payload.get("status")
        or doc.get("status")
        or obj_aut.get("status")
        or ""
    )
    if not status_payload and tipo:
        tl = tipo.lower()
        if tl in (
            "document.finished",
            "signature.accepted",
            "doc_signed",
            "assinado",
        ):
            status_payload = "signed"
        elif tl in ("signature.rejected", "doc_refused", "recusado"):
            status_payload = "refused"

    return (str(token) if token else None), tipo, status_payload


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
        if (
            dados.caso_id is not None
            and self.casos.db.get(Caso, dados.caso_id) is None
        ):
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
        """Atualiza o status quando o provedor (Autentique/ZapSign) avisa."""
        token, tipo, status_payload = _extrair_dados_webhook(payload)
        if not isinstance(token, str) or not token:
            return "ignorado: sem token"

        assinatura = self.assinaturas.buscar_por_token(token)
        if assinatura is None:
            return "ignorado: documento desconhecido"

        status_real = status_payload
        if get_settings().webhooks_verificar_na_api:
            status_real = str(
                self.zapsign.consultar_documento(token).get("status") or ""
            )

        novo = _mapear_status(status_real)
        if novo is None:
            return f"ignorado: status {status_real or '?'}"

        if not self.eventos.registrar(
            "zapsign", f"{token}:{tipo}:{status_real}", tipo or status_real
        ):
            return "duplicado"
        if assinatura.status == ST_ASSINADO:
            self.assinaturas.db.commit()
            return "ja assinado"
        assinatura.status = novo
        if novo == ST_ASSINADO:
            assinatura.assinado_em = datetime.now(timezone.utc).replace(
                tzinfo=None
            )
        self.assinaturas.salvar(assinatura)
        if novo == ST_ASSINADO and assinatura.criado_por:
            GeradorNotificacaoFinanceira(
                NotificacaoService(NotificacaoRepository(self.assinaturas.db))
            ).emitir(
                assinatura.criado_por,
                "DOCUMENTO_ASSINADO",
                "Documento assinado",
                "Um documento enviado para assinatura foi concluído.",
                "/financeiro",
                f"assinatura:{assinatura.id}:assinado",
            )
        return f"status={novo}"


def _mapear_status(status: str) -> str | None:
    s = status.strip().lower()
    if s in ("signed", "assinado", "finished", "accepted"):
        return ST_ASSINADO
    if s in ("refused", "rejected", "recusado"):
        return ST_RECUSADO
    return None
