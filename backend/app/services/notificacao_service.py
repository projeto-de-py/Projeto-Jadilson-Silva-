"""Regras de criação e leitura dos avisos internos do usuário."""

from datetime import date

from sqlalchemy import select

from app.models.caso import Caso
from app.models.notificacao import Notificacao
from app.models.prazo import Prazo
from app.models.usuario import Usuario, utcnow
from app.repositories.escopo import condicao_prazo_visivel
from app.repositories.notificacao_repository import NotificacaoRepository
from sqlalchemy.exc import IntegrityError


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


class GeradorNotificacaoFinanceira(GeradorNotificacaoAcao):
    """Eventos de pagamento/assinatura são enviados ao criador do registro."""


def prazo_vencido_em(data_limite: date, hoje: date | None = None) -> bool:
    """Regra compartilhável com a rotina de varredura de prazos."""
    return data_limite < (hoje or date.today())
