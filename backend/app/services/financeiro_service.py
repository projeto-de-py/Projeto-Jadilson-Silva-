"""Regras financeiras: emitir cobranca de honorarios (Asaas) e acompanhar o pagamento."""

from datetime import date, datetime, timezone
from decimal import Decimal

from app.config import get_settings
from app.models.caso import Caso
from app.models.cobranca import (
    ST_CANCELADA,
    ST_PENDENTE,
    ST_RECEBIDA,
    ST_VENCIDA,
    Cobranca,
)
from app.models.usuario import Usuario
from app.repositories.caso_repository import CasoRepository
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.cobranca_repository import CobrancaRepository
from app.repositories.evento_webhook_repository import EventoWebhookRepository
from app.schemas.financeiro import CobrancaCreate, ResumoFinanceiroOut
from app.services.asaas import AsaasService
from app.repositories.notificacao_repository import NotificacaoRepository
from app.services.notificacao_service import GeradorNotificacaoFinanceira, NotificacaoService


class CobrancaDadosInvalidosError(Exception):
    """Dado de entrada invalido (vira 422)."""


class RegistroNaoEncontradoError(Exception):
    """Cliente, caso ou cobranca inexistente (vira 404)."""


# Eventos que o app trata (o resto e ignorado com 200, para o Asaas nao reenviar).
EVENTOS_TRATADOS = {"PAYMENT_RECEIVED", "PAYMENT_CONFIRMED", "PAYMENT_OVERDUE", "PAYMENT_DELETED"}

_STATUS_ASAAS = {
    "RECEIVED": ST_RECEBIDA,
    "CONFIRMED": ST_RECEBIDA,
    "RECEIVED_IN_CASH": ST_RECEBIDA,
    "OVERDUE": ST_VENCIDA,
    "PENDING": ST_PENDENTE,
    "DELETED": ST_CANCELADA,
    "REFUNDED": ST_CANCELADA,
}
_STATUS_DO_EVENTO = {
    "PAYMENT_RECEIVED": ST_RECEBIDA,
    "PAYMENT_CONFIRMED": ST_RECEBIDA,
    "PAYMENT_OVERDUE": ST_VENCIDA,
    "PAYMENT_DELETED": ST_CANCELADA,
}


def _agora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class FinanceiroService:
    def __init__(
        self,
        cobrancas: CobrancaRepository,
        clientes: ClienteRepository,
        casos: CasoRepository,
        eventos: EventoWebhookRepository,
        asaas: AsaasService,
    ):
        self.cobrancas = cobrancas
        self.clientes = clientes
        self.casos = casos
        self.eventos = eventos
        self.asaas = asaas

    # ---------------------------------------------------------------- emitir

    def emitir(self, dados: CobrancaCreate, operador: Usuario) -> list[Cobranca]:
        s = get_settings()
        if dados.valor > Decimal(str(s.financeiro_valor_maximo)):
            raise CobrancaDadosInvalidosError(
                f"O valor excede o limite de R$ {s.financeiro_valor_maximo:,.2f} por cobranca."
            )
        if dados.vencimento < date.today():
            raise CobrancaDadosInvalidosError("O vencimento nao pode ser uma data passada.")

        cliente = self.clientes.buscar_por_id(dados.cliente_id)
        if cliente is None or not cliente.ativo:
            raise RegistroNaoEncontradoError("Cliente nao encontrado")
        if dados.caso_id is not None and self.casos.db.get(Caso, dados.caso_id) is None:
            raise RegistroNaoEncontradoError("Caso nao encontrado")
        if not cliente.cpf_cnpj:
            raise CobrancaDadosInvalidosError("O cliente precisa ter CPF ou CNPJ cadastrado para receber cobranca.")

        # 1) garante o cliente no Asaas (uma vez so)
        if not cliente.asaas_customer_id:
            cliente.asaas_customer_id = self.asaas.criar_cliente(
                nome=cliente.nome,
                cpf_cnpj=cliente.cpf_cnpj,
                email=cliente.email,
                telefone=cliente.telefone,
            )
            self.clientes.db.add(cliente)
            self.clientes.db.commit()

        # 2) emite a cobranca (o valor vem do servidor/validacao, nunca de texto livre)
        emitidas = self.asaas.criar_cobranca(
            customer_id=cliente.asaas_customer_id,
            forma=dados.forma,
            valor=dados.valor,
            vencimento=dados.vencimento,
            descricao=dados.descricao,
            parcelas=dados.parcelas,
            referencia=f"cliente:{cliente.id}" + (f"|caso:{dados.caso_id}" if dados.caso_id else ""),
        )

        # 3) guarda cada parcela
        total = len(emitidas)
        linhas = []
        for i, p in enumerate(emitidas, start=1):
            linhas.append(Cobranca(
                cliente_id=cliente.id,
                caso_id=dados.caso_id,
                asaas_payment_id=p["id"],
                asaas_installment_id=p.get("installment"),
                forma=dados.forma,
                valor=Decimal(str(p.get("value", dados.valor if total == 1 else dados.valor / total))).quantize(Decimal("0.01")),
                vencimento=date.fromisoformat(p["dueDate"]) if p.get("dueDate") else dados.vencimento,
                descricao=dados.descricao,
                parcela=i,
                total_parcelas=total,
                status=_STATUS_ASAAS.get(str(p.get("status", "PENDING")), ST_PENDENTE),
                link_fatura=p.get("invoiceUrl"),
                criado_por=operador.id,
            ))
        return self.cobrancas.adicionar_varias(linhas)

    # ---------------------------------------------------------------- resumo

    def resumo(self, cliente_id: int) -> ResumoFinanceiroOut:
        if self.clientes.buscar_por_id(cliente_id) is None:
            raise RegistroNaoEncontradoError("Cliente nao encontrado")
        t = self.cobrancas.totais_por_status(cliente_id)
        def soma(st: str) -> Decimal:
            return t.get(st, (0, Decimal("0")))[1].quantize(Decimal("0.01"))

        return ResumoFinanceiroOut(
            cliente_id=cliente_id,
            pendente=soma(ST_PENDENTE),
            recebido=soma(ST_RECEBIDA),
            vencido=soma(ST_VENCIDA),
            cancelado=soma(ST_CANCELADA),
            em_dia=t.get(ST_VENCIDA, (0, 0))[0] == 0,
        )

    # --------------------------------------------------------------- webhook

    def processar_webhook(self, payload: dict) -> str:
        evento = str(payload.get("event") or "")
        if evento not in EVENTOS_TRATADOS:
            return f"ignorado: evento {evento or '?'}"
        pagamento = payload.get("payment") if isinstance(payload.get("payment"), dict) else {}
        payment_id = pagamento.get("id")
        if not isinstance(payment_id, str) or not payment_id:
            return "ignorado: sem pagamento"

        cobranca = self.cobrancas.buscar_por_pagamento(payment_id)
        if cobranca is None:
            return "ignorado: cobranca desconhecida"

        novo = _STATUS_DO_EVENTO[evento]
        if get_settings().webhooks_verificar_na_api:
            # Nao confia so no aviso: pergunta ao Asaas como a cobranca esta de verdade.
            real = self.asaas.consultar_pagamento(payment_id)
            novo = _STATUS_ASAAS.get(str(real.get("status") or ""), cobranca.status)

        evento_id = str(payload.get("id") or f"{payment_id}:{evento}")
        if not self.eventos.registrar("asaas", evento_id, evento):
            return "duplicado"

        # Recebida nunca volta para vencida/pendente por um evento atrasado.
        if cobranca.status == ST_RECEBIDA and novo != ST_CANCELADA:
            self.cobrancas.db.commit()
            return "ja recebida"
        status_anterior = cobranca.status
        cobranca.status = novo
        if novo == ST_RECEBIDA and cobranca.pago_em is None:
            cobranca.pago_em = _agora()
        self.cobrancas.salvar(cobranca)
        if cobranca.criado_por and novo in (ST_RECEBIDA, ST_VENCIDA) and status_anterior != novo:
            recebido = novo == ST_RECEBIDA
            GeradorNotificacaoFinanceira(NotificacaoService(NotificacaoRepository(self.cobrancas.db))).emitir(
                cobranca.criado_por,
                "PAGAMENTO_RECEBIDO" if recebido else "PAGAMENTO_VENCIDO",
                "Pagamento confirmado" if recebido else "Cobrança vencida",
                "Um pagamento foi confirmado." if recebido else "Uma cobrança atingiu a data de vencimento.",
                "/financeiro",
                f"cobranca:{cobranca.id}:status:{novo}",
            )
        return f"status={novo}"
