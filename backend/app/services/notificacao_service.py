"""Regras de criação e leitura dos avisos internos do usuário."""

from datetime import date, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.models.caso import Caso
from app.models.evento_agenda import EventoAgenda
from app.models.notificacao import Notificacao
from app.models.prazo import Prazo
from app.models.usuario import Usuario, utcnow
from app.repositories.escopo import condicao_caso_visivel, condicao_prazo_visivel
from app.repositories.notificacao_repository import NotificacaoRepository

MODELOS_TESTE_NOTIFICACAO: dict[str, dict[str, str]] = {
    "prazoHoje": {
        "tipo": "PRAZO",
        "titulo": "Prazo vence hoje",
        "mensagem": "Há um prazo processual fatal com vencimento hoje.",
        "link": "/prazos",
        "severidade": "critica",
    },
    "prazo3dias": {
        "tipo": "PRAZO",
        "titulo": "Prazo próximo",
        "mensagem": "Um prazo processual vence nos próximos 3 dias.",
        "link": "/prazos",
        "severidade": "atencao",
    },
    "audiencias": {
        "tipo": "AUDIENCIA",
        "titulo": "Audiência agendada",
        "mensagem": "Lembrete: você possui uma audiência agendada nas próximas 24 horas.",
        "link": "/agenda",
        "severidade": "atencao",
    },
    "novosClientes": {
        "tipo": "CLIENTE_CADASTRADO",
        "titulo": "Novo cadastro disponível",
        "mensagem": "Um novo cadastro de cliente foi adicionado ao escritório.",
        "link": "/clientes",
        "severidade": "info",
    },
    "relatorioSemanal": {
        "tipo": "RELATORIO_SEMANAL",
        "titulo": "Relatório semanal da carteira",
        "mensagem": "Resumo semanal de sexta-feira da carteira disponível no painel.",
        "link": "/home",
        "severidade": "info",
    },
}


class NotificacaoService:
    def __init__(self, repo: NotificacaoRepository):
        self.repo = repo

    def criar(self, *, usuario_id: int, tipo: str, titulo: str, mensagem: str, link: str, severidade: str, chave_dedupe: str):
        if self.repo.buscar_dedupe(usuario_id, chave_dedupe):
            return None
        try:
            return self.repo.criar(Notificacao(usuario_id=usuario_id, tipo=tipo, titulo=titulo[:120], mensagem=mensagem[:240], link=link[:300], severidade=severidade, chave_dedupe=chave_dedupe[:180]))
        except IntegrityError:
            # O UNIQUE fecha a corrida entre duas rotinas que gerem o mesmo aviso.
            self.repo.db.rollback()
            if self.repo.buscar_dedupe(usuario_id, chave_dedupe[:180]) is not None:
                return None
            raise

    def listar(self, usuario_id: int, *, pagina: int, limite: int, lidas: bool | None):
        itens, lista = self.repo.listar(usuario_id, pagina=pagina, limite=limite, lidas=lidas)
        return {"itens": lista, "total": itens, "pagina": pagina, "limite": limite}

    def contar_nao_lidas(self, usuario_id: int) -> int:
        return self.repo.contar_nao_lidas(usuario_id)

    def marcar_lida(self, usuario_id: int, notificacao_id: int):
        return self.repo.marcar_lida(usuario_id, notificacao_id, utcnow())

    def marcar_todas_lidas(self, usuario_id: int) -> int:
        return self.repo.marcar_todas_lidas(usuario_id, utcnow())

    def limpar_todas(self, usuario_id: int) -> int:
        return self.repo.limpar_todas(usuario_id, utcnow())

    def emitir_teste(self, usuario_id: int, *, tipos: list[str] | None = None) -> list[Notificacao]:
        chaves = tipos if tipos else list(MODELOS_TESTE_NOTIFICACAO.keys())
        criadas: list[Notificacao] = []
        for chave in chaves:
            modelo = MODELOS_TESTE_NOTIFICACAO.get(chave)
            if modelo is None:
                continue
            item = self.criar(
                usuario_id=usuario_id,
                tipo=modelo["tipo"],
                titulo=f"[Teste] {modelo['titulo']}",
                mensagem=modelo["mensagem"],
                link=modelo["link"],
                severidade=modelo["severidade"],
                chave_dedupe=f"teste:{chave}:{uuid4().hex}",
            )
            if item is not None:
                criadas.append(item)
        return criadas


class GeradorNotificacaoPrazo:
    """Cria avisos de prazo na primeira leitura; a chave torna a varredura repetível."""

    MARCOS = {7: ("info", "Prazo se aproxima", "Um prazo processual vence em 7 dias."), 3: ("atencao", "Prazo próximo", "Um prazo processual vence em 3 dias."), 1: ("atencao", "Prazo amanhã", "Um prazo processual vence amanhã."), 0: ("critica", "Prazo vence hoje", "Há um prazo processual com vencimento hoje.")}

    def __init__(self, repo: NotificacaoRepository):
        self.repo = repo

    def gerar_para(self, usuario: Usuario) -> None:
        hoje = date.today()
        prazos = self.repo.db.scalars(select(Prazo).join(Caso).where(Prazo.cumprido.is_(False), condicao_prazo_visivel(usuario))).all()
        service = NotificacaoService(self.repo)
        for prazo in prazos:
            dias = (prazo.data_limite - hoje).days
            if dias in self.MARCOS:
                severidade, titulo, mensagem = self.MARCOS[dias]
            elif dias < 0:
                severidade, titulo, mensagem = "critica", "Prazo vencido", "Há um prazo processual vencido que precisa de atenção."
            else:
                continue
            marco = "vencido" if dias < 0 else f"marco-{dias}"
            service.criar(usuario_id=usuario.id, tipo="PRAZO", titulo=titulo, mensagem=mensagem, link="/prazos", severidade=severidade, chave_dedupe=f"prazo:{prazo.id}:{prazo.data_limite.isoformat()}:{marco}")


class GeradorNotificacaoAudiencia:
    """Cria lembretes de audiências agendadas nas próximas 24 horas."""

    TIPOS_AUDIENCIA = ("AUDIENCIA", "AUDIENCIA_VIRTUAL", "CONCILIACAO")

    def __init__(self, repo: NotificacaoRepository):
        self.repo = repo

    def gerar_para(self, usuario: Usuario, agora: datetime | None = None) -> None:
        referencia = agora or datetime.now()
        limite = referencia + timedelta(hours=24)
        stmt = select(EventoAgenda).where(
            EventoAgenda.tipo.in_(self.TIPOS_AUDIENCIA),
            EventoAgenda.inicio >= referencia - timedelta(hours=2),
            EventoAgenda.inicio <= limite,
            or_(
                EventoAgenda.destinatario_id.is_(None),
                EventoAgenda.destinatario_id == usuario.id,
                EventoAgenda.criado_por_id == usuario.id,
            ),
        )
        eventos = self.repo.db.scalars(stmt).all()
        service = NotificacaoService(self.repo)
        for evento in eventos:
            service.criar(
                usuario_id=usuario.id,
                tipo="AUDIENCIA",
                titulo="Audiência agendada",
                mensagem="Lembrete: você possui uma audiência agendada nas próximas 24 horas.",
                link="/agenda",
                severidade="atencao",
                chave_dedupe=f"audiencia:{evento.id}:{evento.inicio.date().isoformat()}:24h",
            )


class GeradorNotificacaoRelatorioSemanal:
    """Cria o resumo semanal da carteira toda sexta-feira."""

    def __init__(self, repo: NotificacaoRepository):
        self.repo = repo

    def gerar_para(self, usuario: Usuario, hoje: date | None = None) -> None:
        dia = hoje or date.today()
        if dia.weekday() != 4:  # 4 = sexta-feira
            return
        total_casos = int(
            self.repo.db.scalar(
                select(func.count())
                .select_from(Caso)
                .where(Caso.arquivado.is_(False), condicao_caso_visivel(usuario))
            )
            or 0
        )
        total_prazos = int(
            self.repo.db.scalar(
                select(func.count())
                .select_from(Prazo)
                .join(Caso)
                .where(Prazo.cumprido.is_(False), condicao_prazo_visivel(usuario))
            )
            or 0
        )
        iso = dia.isocalendar()
        NotificacaoService(self.repo).criar(
            usuario_id=usuario.id,
            tipo="RELATORIO_SEMANAL",
            titulo="Relatório semanal da carteira",
            mensagem=f"Resumo de sexta-feira: {total_casos} processo(s) ativo(s) e {total_prazos} prazo(s) pendente(s).",
            link="/home",
            severidade="info",
            chave_dedupe=f"relatorio-semanal:{iso.year}-W{iso.week:02d}",
        )


def sincronizar_notificacoes_automaticas(repo: NotificacaoRepository, usuario: Usuario) -> None:
    """Dispara os geradores periódicos (prazos, audiências em 24h e relatório de sexta-feira)."""
    GeradorNotificacaoPrazo(repo).gerar_para(usuario)
    GeradorNotificacaoAudiencia(repo).gerar_para(usuario)
    GeradorNotificacaoRelatorioSemanal(repo).gerar_para(usuario)


class GeradorNotificacaoAcao:
    """Fábrica curta para eventos de negócio sem transportar dados pessoais."""

    def __init__(self, service: NotificacaoService):
        self.service = service

    def emitir(self, usuario_id: int, tipo: str, titulo: str, mensagem: str, link: str, chave: str):
        return self.service.criar(usuario_id=usuario_id, tipo=tipo, titulo=titulo, mensagem=mensagem, link=link, severidade="info", chave_dedupe=chave)

    def emitir_para_ativos(self, usuario_ids: list[int], tipo: str, titulo: str, mensagem: str, link: str, chave: str):
        for usuario_id in set(usuario_ids):
            self.emitir(usuario_id, tipo, titulo, mensagem, link, f"{chave}:usuario:{usuario_id}")


class GeradorNotificacaoCliente(GeradorNotificacaoAcao):
    def cadastrado(self, usuario_ids: list[int], cliente_id: int) -> None:
        self.emitir_para_ativos(usuario_ids, "CLIENTE_CADASTRADO", "Novo cadastro disponível", "Um novo cadastro foi adicionado ao escritório.", "/clientes", f"cliente:{cliente_id}:criado")


class GeradorNotificacaoCaso(GeradorNotificacaoAcao):
    def atribuido(self, usuario_id: int, caso_id: int) -> None:
        self.emitir(usuario_id, "CASO_ATRIBUIDO", "Novo caso atribuído", "Um novo caso foi atribuído a você.", "/processos", f"caso:{caso_id}:atribuido:{usuario_id}")


class GeradorNotificacaoColaborador(GeradorNotificacaoAcao):
    def acesso_alterado(self, usuario_id: int, caso_id: int, concedido: bool, evento_id: str) -> None:
        titulo = "Acesso concedido a um caso" if concedido else "Acesso removido de um caso"
        mensagem = "Um caso foi compartilhado com você." if concedido else "Seu acesso a um caso foi removido."
        acao = "concedido" if concedido else "revogado"
        self.emitir(usuario_id, f"COLABORADOR_{acao.upper()}", titulo, mensagem, "/processos", f"caso:{caso_id}:acesso:{acao}:{evento_id}")


class GeradorNotificacaoAgenda(GeradorNotificacaoAcao):
    def evento_criado(
        self,
        usuario_ids: list[int],
        evento_id: int,
        titulo_evento: str,
        inicio_evento: datetime,
        criador_nome: str,
        tipo_evento: str | None = None,
    ) -> None:
        data_formatada = inicio_evento.strftime("%d/%m/%Y às %H:%M")
        rotulo = "Audiência" if tipo_evento in ("AUDIENCIA", "AUDIENCIA_VIRTUAL", "CONCILIACAO") else "Evento"
        severidade = "atencao" if rotulo == "Audiência" else "info"
        titulo = "Novo compromisso na agenda"
        mensagem = f"{criador_nome} agendou '{titulo_evento}' ({rotulo}) para {data_formatada}."
        for uid in set(usuario_ids):
            self.service.criar(
                usuario_id=uid,
                tipo="AGENDA_EVENTO",
                titulo=titulo,
                mensagem=mensagem,
                link="/agenda",
                severidade=severidade,
                chave_dedupe=f"agenda:evento:{evento_id}:criado:usuario:{uid}",
            )


class GeradorNotificacaoFinanceira(GeradorNotificacaoAcao):
    """Eventos de pagamento/assinatura são enviados ao criador do registro."""


def prazo_vencido_em(data_limite: date, hoje: date | None = None) -> bool:
    """Regra compartilhável com a rotina de varredura de prazos."""
    return data_limite < (hoje or date.today())
