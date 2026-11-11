"""Autentique (GraphQL v2): envio gratuito de documentos para assinatura eletronica + webhook.

Documentacao oficial: https://docs.autentique.com.br/api
Plano gratuito: ate 10 documentos/mes com validade juridica (MP 2.200-2/2001 e Lei 14.063/2020)
e suporte a webhooks (eventos `document.finished`, `signature.accepted`, `signature.rejected`).

Implementa a mesma interface do cliente de assinatura (`criar_documento` e `consultar_documento`)
para que `AssinaturaService` funcione de forma transparente com Autentique ou ZapSign.
"""

import base64
import json

import httpx

from app.config import get_settings
from app.integrations.base import ClienteHttp
from app.integrations.erros import IntegracaoErro
from app.services.zapsign import so_digitos

MUTATION_CRIAR_DOCUMENTO = """
mutation CreateDocumentMutation(
  $document: DocumentInput!,
  $signers: [SignerInput!]!,
  $file: Upload!
) {
  createDocument(
    sandbox: $sandbox,
    document: $document,
    signers: $signers,
    file: $file
  ) {
    id
    name
    signatures {
      public_id
      name
      email
      link {
        short_link
      }
    }
  }
}
"""

QUERY_CONSULTAR_DOCUMENTO = """
query ConsultarDocumento($id: UUID!) {
  document(id: $id) {
    id
    name
    signatures {
      public_id
      signed {
        created_at
      }
      rejected {
        created_at
      }
    }
  }
}
"""


class AutentiqueService(ClienteHttp):
    servico = "Autentique"

    def __init__(
        self,
        token: str | None,
        base_url: str = "https://api.autentique.com.br/v2/graphql",
        sandbox: bool = False,
        http: httpx.Client | None = None,
        timeout: int = 20,
    ):
        super().__init__(base_url, http=http, timeout=timeout)
        self._token = token
        self._sandbox = sandbox

    @classmethod
    def do_ambiente(cls, http: httpx.Client | None = None) -> "AutentiqueService":
        s = get_settings()
        token = (
            s.autentique_api_token.get_secret_value()
            if s.autentique_api_token
            else None
        )
        return cls(
            token=token,
            base_url=s.autentique_api_url,
            sandbox=s.autentique_sandbox,
            http=http,
            timeout=s.integracao_timeout_segundos,
        )

    def _cabecalhos_auth(self) -> dict[str, str]:
        if not self._token:
            raise self._nao_configurada()
        return {"Authorization": f"Bearer {self._token}"}

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
        """Envia o PDF via multipart GraphQL (`createDocument`) para o Autentique."""
        headers = self._cabecalhos_auth()
        fone = so_digitos(signatario_telefone)
        if fone and not fone.startswith("55") and len(fone) in (10, 11):
            fone = f"55{fone}"

        signatario: dict = {
            "name": signatario_nome,
            "action": "SIGN",
        }
        if signatario_email:
            signatario["email"] = signatario_email
        elif fone:
            signatario["phone"] = f"+{fone}"
            signatario["delivery_method"] = "DELIVERY_METHOD_WHATSAPP"

        documento_input: dict = {"name": nome}
        if mensagem:
            documento_input["message"] = mensagem[:500]

        query = MUTATION_CRIAR_DOCUMENTO.replace(
            "$sandbox", "true" if self._sandbox else "false"
        )
        operations = {
            "query": query,
            "variables": {
                "document": documento_input,
                "signers": [signatario],
                "file": None,
            },
        }
        mapa = {"0": ["variables.file"]}
        pdf_bytes = base64.b64decode(pdf_base64)

        try:
            if self._http is not None:
                resp = self._http.post(
                    self.base_url,
                    headers=headers,
                    data={
                        "operations": json.dumps(operations),
                        "map": json.dumps(mapa),
                    },
                    files={"0": (f"{nome[:40] or 'documento'}.pdf", pdf_bytes, "application/pdf")},
                    timeout=self._timeout,
                )
            else:
                with httpx.Client(timeout=self._timeout) as cliente:
                    resp = cliente.post(
                        self.base_url,
                        headers=headers,
                        data={
                            "operations": json.dumps(operations),
                            "map": json.dumps(mapa),
                        },
                        files={"0": (f"{nome[:40] or 'documento'}.pdf", pdf_bytes, "application/pdf")},
                    )
        except httpx.HTTPError as exc:
            raise IntegracaoErro(
                self.servico, "Nao foi possivel conectar ao Autentique."
            ) from exc

        if resp.status_code >= 400:
            raise IntegracaoErro(
                self.servico,
                f"Autentique respondeu HTTP {resp.status_code}.",
                status_http=resp.status_code,
            )

        dados = resp.json() if resp.content else {}
        if dados.get("errors"):
            msg = dados["errors"][0].get("message") or "Erro GraphQL no Autentique."
            raise IntegracaoErro(self.servico, msg)

        criado = (dados.get("data") or {}).get("createDocument") or {}
        doc_id = criado.get("id")
        if not doc_id:
            raise IntegracaoErro(
                self.servico,
                "O Autentique nao devolveu o identificador do documento.",
            )

        assinaturas = criado.get("signatures") or []
        primeira = next(
            (s for s in assinaturas if isinstance(s, dict) and s.get("link")),
            assinaturas[0] if assinaturas else {},
        )
        link_obj = primeira.get("link") if isinstance(primeira, dict) else {}
        short_link = (
            link_obj.get("short_link") if isinstance(link_obj, dict) else None
        )
        return {
            "token": str(doc_id),
            "link": short_link,
            "signer_token": primeira.get("public_id")
            if isinstance(primeira, dict)
            else None,
        }

    def consultar_documento(self, token: str) -> dict:
        """Consulta o estado atual do documento no Autentique e normaliza `status`."""
        headers = {**self._cabecalhos_auth(), "Content-Type": "application/json"}
        corpo = {
            "query": QUERY_CONSULTAR_DOCUMENTO,
            "variables": {"id": token},
        }
        r = self._chamar("POST", "", json=corpo, headers=headers)
        if r.get("errors"):
            msg = r["errors"][0].get("message") or "Erro ao consultar documento no Autentique."
            raise IntegracaoErro(self.servico, msg)

        doc = (r.get("data") or {}).get("document") or {}
        assinaturas = doc.get("signatures") or []
        algum_recusado = any(
            isinstance(s, dict) and s.get("rejected") for s in assinaturas
        )
        todos_assinados = bool(assinaturas) and all(
            isinstance(s, dict) and s.get("signed")
            for s in assinaturas
            if isinstance(s, dict)
        )
        if algum_recusado:
            status = "refused"
        elif todos_assinados:
            status = "signed"
        else:
            status = "pending"
        return {"token": token, "status": status}
