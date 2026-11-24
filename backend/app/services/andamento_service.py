"""Service Layer: andamentos juridicos - historico de movimentacoes (RF06).

Regras principais:
- leitura: herda o escopo de visibilidade do caso (Fase 1) - um andamento
  fora do escopo responde 404, nunca revelando a existencia de casos alheios;
- escrita (registrar): admin, advogado responsavel pelo caso ou usuario com a
  concessao `pode_registrar_andamento` ativa (mesmo padrao granular das Fases
  3/4, com a permissao propria da tabela `usuario_casos`);
- o usuario responsavel pelo registro e SEMPRE o operador autenticado
  (`criado_por_id`), obtido da sessao - o payload nao aceita esse campo;
- caso arquivado nao recebe novos andamentos (mesma regra de prazos e
  compromissos);
- `ocorrido_em` e horario LOCAL de Brasilia (naive): quando nao informado, o
  service grava o instante atual local - nunca UTC misturado na UI;
- IMUTABILIDADE: nao existe atualizacao nem exclusao de andamento. Um registro
  gravado permanece; correcoes sao feitas por registro COMPLEMENTAR (novo
  andamento que retifica o anterior), preservando o historico original;
- ATOMICIDADE: o registro nasce em UMA transacao (`_transacao`) - ou o
  andamento persiste inteiro, ou nada persiste.
"""

from contextlib import contextmanager

from app.core.tempo import agora_brasilia
from app.models.andamento import Andamento
from app.models.caso import Caso
from app.models.usuario import Usuario
from app.repositories.andamento_repository import AndamentoRepository
from app.repositories.caso_repository import CasoRepository
from app.repositories.usuario_caso_repository import UsuarioCasoRepository
from app.schemas.andamento import AndamentoCreate
from app.services.caso_service import CasoNaoEncontradoError
from app.services.cliente_service import DadosInvalidosError


class AndamentoNaoEncontradoError(Exception):
    """Andamento inexistente ou fora do escopo do usuario (404)."""


class AndamentoSemPermissaoError(Exception):
    """Registro de andamento sem a permissao necessaria no caso (403)."""


class AndamentoService:
    def __init__(
        self,
        andamentos: AndamentoRepository,
        casos: CasoRepository,
        permissoes: UsuarioCasoRepository,
    ):
        self.andamentos = andamentos
        self.casos = casos
        self.permissoes = permissoes

    # ------------------------------------------------------------- leitura

    def listar(
        self,
        caso_id: int,
        usuario: Usuario,
        *,
        pagina: int = 1,
        limite: int = 20,
        ordem: str = "desc",
    ) -> dict:
        """Andamentos de um caso sob o escopo do usuario (paginado no banco)."""
        caso = self._caso_ou_erro(caso_id, usuario)
        total, rows = self.andamentos.listar(
            caso_id=caso.id,
            usuario=usuario,
            pagina=pagina,
            limite=limite,
            ordem=ordem,
        )
        return {
            "itens": [self._serializar(item, nome) for item, nome in rows],
            "total": total,
            "pagina": pagina,
            "limite": limite,
        }

    def buscar(
        self, caso_id: int, andamento_id: int, usuario: Usuario
    ) -> dict:
        self._caso_ou_erro(caso_id, usuario)  # mesmo escopo do caso
        registro = self.andamentos.buscar_visivel(andamento_id, usuario)
        if registro is None or registro[0].caso_id != caso_id:
            # andamento de OUTRO caso responde 404 (nao vaza vinculo)
            raise AndamentoNaoEncontradoError("Andamento nao encontrado")
        item, nome = registro
        return self._serializar(item, nome)

    # ------------------------------------------------------------- criacao

    def criar(self, caso_id: int, dados: AndamentoCreate, operador: Usuario) -> dict:
        caso = self._caso_ou_erro(caso_id, operador)
        self._pode_registrar(caso, operador)

        if caso.arquivado:
            # um caso arquivado nao recebe novos andamentos (mesma regra da
            # Fase 4): o historico existente continua consultavel.
            raise DadosInvalidosError(
                "Nao e possivel registrar andamento em um caso arquivado"
            )

        andamento = Andamento(
            caso_id=caso.id,
            titulo=dados.titulo,
            descricao=dados.descricao,
            # Sempre local de Brasilia (naive): ou o horario informado pelo
            # operador (ja convertido no schema), ou o instante atual local.
            ocorrido_em=dados.ocorrido_em or agora_brasilia(),
            # Responsavel = SESSAO autenticada; o payload nem aceita o campo.
            criado_por_id=operador.id,
        )
        with self._transacao():
            andamento = self.andamentos.criar(andamento)
        return self._serializar(andamento, operador.nome)

    # ------------------------------------------------------------- privado

    @contextmanager
    def _transacao(self):
        """Uma unica transacao para o registro do andamento.

        Nenhum commit intermediario: o `flush` do repository e o commit final
        acontecem aqui. Qualquer falha chama `rollback()`, desfazendo o
        registro - nao existe andamento gravado parcialmente.
        """
        try:
            yield
        except BaseException:
            self.andamentos.desfazer()
            raise
        else:
            self.andamentos.confirmar()

    def _caso_ou_erro(self, caso_id: int, usuario: Usuario) -> Caso:
        """Caso acessivel ao usuario (escopo Fase 1) - senao 404."""
        caso = self.casos.buscar_visivel(caso_id, usuario, incluir_arquivados=True)
        if caso is None:
            raise CasoNaoEncontradoError("Caso nao encontrado")
        return caso

    def _pode_registrar(self, caso: Caso, operador: Usuario) -> None:
        """Admin, advogado responsavel pelo caso ou com `pode_registrar_andamento`."""
        if operador.administrador:
            return
        if caso.responsavel_id == operador.id:
            return
        linha = self.permissoes.buscar(operador.id, caso.id)
        if linha is not None and linha.ativo and linha.pode_registrar_andamento:
            return
        raise AndamentoSemPermissaoError(
            "Sem permissao para registrar andamentos neste caso"
        )

    @staticmethod
    def _serializar(andamento: Andamento, criado_por_nome: str | None) -> dict:
        """DTO do andamento (historico imutavel - sem campos de edicao)."""
        return {
            "id": andamento.id,
            "caso_id": andamento.caso_id,
            "titulo": andamento.titulo,
            "descricao": andamento.descricao,
            "ocorrido_em": andamento.ocorrido_em,
            "criado_por": andamento.criado_por_id,
            "criado_por_nome": criado_por_nome,
        }
