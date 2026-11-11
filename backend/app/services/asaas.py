"""Asaas: clientes e cobrancas (Pix e boleto) de honorarios.

Documentacao oficial: https://docs.asaas.com - confira nomes de campos ao ligar em
producao. A URL padrao e a do SANDBOX; producao so com ASAAS_API_URL trocada.

Este e um CLIENTE: so fala HTTP com o Asaas. As regras (valor maximo, vencimento,
quem pode cobrar, guardar no banco) ficam em `financeiro_service.py`.
"""

from datetime import date
from decimal import Decimal

import httpx

from app.config import get_settings
from app.integrations.base import ClienteHttp
from app.integrations.erros import IntegracaoErro

MAX_PARCELAS = 24


class AsaasService(ClienteHttp):
    servico = "Asaas"

    def __init__(self, api_key: str | None, base_url: str, http: httpx.Client | None = None, timeout: int = 20):
        super().__init__(base_url, http=http, timeout=timeout)
        self._key = api_key

    @classmethod
    def do_ambiente(cls, http: httpx.Client | None = None) -> "AsaasService":
        """Monta o cliente com a configuracao do .env (ASAAS_*)."""
        s = get_settings()
        chave = s.asaas_api_key.get_secret_value() if s.asaas_api_key else None
        return cls(chave, s.asaas_api_url, http, s.integracao_timeout_segundos)

    def _cabecalhos(self) -> dict:
        if not self._key:
            raise self._nao_configurada()
        return {"access_token": self._key, "Content-Type": "application/json", "User-Agent": "jadilson-adv"}

    # ---------------------------------------------------------------- clientes

    def criar_cliente(self, *, nome: str, cpf_cnpj: str, email: str | None, telefone: str | None) -> str:
        """Cadastra o cliente no Asaas e devolve o id. Reaproveita se o documento ja existir la."""
        existente = self._chamar("GET", "/customers", params={"cpfCnpj": cpf_cnpj, "limit": 1})
        dados = existente.get("data") or []
        if dados and isinstance(dados[0], dict) and dados[0].get("id"):
            return dados[0]["id"]
        corpo = {"name": nome, "cpfCnpj": cpf_cnpj, "notificationDisabled": False}
        if email:
            corpo["email"] = email
        if telefone:
            corpo["mobilePhone"] = telefone
        criado = self._chamar("POST", "/customers", json=corpo)
        if not criado.get("id"):
            raise IntegracaoErro(self.servico, "O Asaas nao devolveu o identificador do cliente.")
        return criado["id"]

    # --------------------------------------------------------------- cobrancas

    def criar_cobranca(
        self,
        *,
        customer_id: str,
        forma: str,
        valor: Decimal,
        vencimento: date,
        descricao: str | None,
        parcelas: int = 1,
        referencia: str | None = None,
    ) -> list[dict]:
        """Emite a cobranca. Parcelada devolve uma lista, uma por parcela (ja com status)."""
        corpo: dict = {
            "customer": customer_id,
            "billingType": forma,
            "dueDate": vencimento.isoformat(),
            "description": (descricao or "Honorarios advocaticios")[:200],
        }
        if referencia:
            corpo["externalReference"] = referencia[:100]
        if parcelas > 1:
            corpo["installmentCount"] = parcelas
            corpo["totalValue"] = float(valor)
        else:
            corpo["value"] = float(valor)

        criada = self._chamar("POST", "/payments", json=corpo)
        if not criada.get("id"):
            raise IntegracaoErro(self.servico, "O Asaas nao devolveu o identificador da cobranca.")
        if parcelas > 1 and criada.get("installment"):
            lista = self._chamar("GET", f"/installments/{criada['installment']}/payments")
            itens = [p for p in (lista.get("data") or []) if isinstance(p, dict) and p.get("id")]
            if itens:
                return itens
        return [criada]

    def consultar_pagamento(self, payment_id: str) -> dict:
        """Estado atual da cobranca no Asaas (usado para confirmar webhooks)."""
        return self._chamar("GET", f"/payments/{payment_id}")
