"""ZapSign: envio de documentos para assinatura eletronica (WhatsApp/e-mail).

Documentacao oficial: https://docs.zapsign.com.br - confira nomes de campos e valores
de `status` la ao ligar em producao; o codigo le a resposta de forma defensiva
(campo ausente nao derruba o fluxo).

Este e um CLIENTE: so fala HTTP com o ZapSign. As regras (quem pode enviar, validar o PDF,
guardar no banco) ficam em `assinatura_service.py`.
"""

import re

import httpx

from app.config import get_settings
from app.integrations.base import ClienteHttp
from app.integrations.erros import IntegracaoErro


def so_digitos(texto: str | None) -> str:
    return re.sub(r"\D", "", texto or "")


class ZapSignService(ClienteHttp):
    servico = "ZapSign"

    def __init__(self, token: str | None, base_url: str, http: httpx.Client | None = None, timeout: int = 20):
        super().__init__(base_url, http=http, timeout=timeout)
        self._token = token

    @classmethod
    def do_ambiente(cls, http: httpx.Client | None = None) -> "ZapSignService":
        """Monta o cliente com a configuracao do .env (ZAPSIGN_*)."""
        s = get_settings()
        token = s.zapsign_api_token.get_secret_value() if s.zapsign_api_token else None
        return cls(token, s.zapsign_api_url, http, s.integracao_timeout_segundos)

    def _cabecalhos(self) -> dict:
        if not self._token:
            raise self._nao_configurada()
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    def criar_documento(
        self,
        *,
        nome: str,
        pdf_base64: str,
        signatario_nome: str,
        signatario_email: str | None,
        signatario_telefone: str | None,
        mensagem: str | None = None,
    ) -> dict:
        """Cria o documento e o signatario. Devolve {token, link, signer_token}."""
        fone = so_digitos(signatario_telefone)
        if fone.startswith("55") and len(fone) > 11:
            fone = fone[2:]  # o pais vai em campo proprio
        signatario = {
            "name": signatario_nome,
            "email": signatario_email or "",
            "auth_mode": "assinaturaTela",
            "send_automatic_email": bool(signatario_email),
            "send_automatic_whatsapp": bool(fone),
        }
        if fone:
            signatario.update({"phone_country": "55", "phone_number": fone})
        corpo = {"name": nome, "base64_pdf": pdf_base64, "lang": "pt-br", "signers": [signatario]}
        if mensagem:
            corpo["observation"] = mensagem[:500]

        r = self._chamar("POST", "/docs/", json=corpo)
        token = r.get("token")
        if not token:
            raise IntegracaoErro(self.servico, "O ZapSign nao devolveu o identificador do documento.")
        signers = r.get("signers") or [{}]
        primeiro = signers[0] if isinstance(signers[0], dict) else {}
        return {"token": token, "link": primeiro.get("sign_url"), "signer_token": primeiro.get("token")}

    def consultar_documento(self, token: str) -> dict:
        """Estado atual do documento no ZapSign (usado para confirmar webhooks)."""
        return self._chamar("GET", f"/docs/{token}/")
