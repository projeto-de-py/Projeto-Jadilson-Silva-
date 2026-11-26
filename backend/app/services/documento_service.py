"""Service Layer: documentos redigidos no escritorio (Fase 3).

Regras:
- leitura herda o escopo do caso (Repository + `condicao_documento_visivel`);
- escrita exige admin, advogado responsavel pelo caso ou a concessao
  `pode_gerenciar_processos` (a peca e um ato do processo);
- documento sem caso e privado do advogado principal — nao ha escopo para
  inferir, entao ninguem mais cria, edita, move ou exclui;
- `cliente_id` e `pasta_id` sao apenas organizacao da tela. Se o documento
  tambem tem caso, o cliente informado tem que ser o cliente daquele caso;
- mover de pasta NAO muda `atualizado_em` (nao e edicao de conteudo).
"""

from typing import Any

from app.models.caso import Caso
from app.models.documento import Documento
from app.models.usuario import Usuario, utcnow
from app.repositories.caso_repository import CasoRepository
from app.repositories.documento_repository import DocumentoRepository
from app.repositories.usuario_caso_repository import UsuarioCasoRepository
from app.schemas.documento import (
    DocumentoCreate,
    DocumentoMover,
    DocumentoUpdate,
)
from app.services.caso_service import CasoNaoEncontradoError
from app.services.cliente_service import DadosInvalidosError


class DocumentoNaoEncontradoError(Exception):
    """Documento inexistente OU fora do escopo - ambos respondem 404."""


class DocumentoSemPermissaoError(Exception):
    """Operacao de escrita negada (403)."""


class DocumentoService:
    def __init__(
        self,
        documentos: DocumentoRepository,
        casos: CasoRepository,
        permissoes: UsuarioCasoRepository,
    ):
        self.documentos = documentos
        self.casos = casos
        self.permissoes = permissoes

    # ------------------------------------------------------------- leitura

    def listar(self, usuario: Usuario, **filtros: Any) -> dict:
        itens, total = self.documentos.listar(usuario=usuario, **filtros)
        return {
            "itens": itens,
            "total": total,
            "pagina": filtros.get("pagina", 1),
            "limite": filtros.get("limite", 20),
        }

    def buscar(self, documento_id: int, usuario: Usuario) -> Documento:
        documento = self.documentos.buscar_visivel(documento_id, usuario)
        if documento is None:
            raise DocumentoNaoEncontradoError("Documento nao encontrado")
        return documento

    # ------------------------------------------------------------- criacao

    def criar(self, dados: DocumentoCreate, operador: Usuario) -> Documento:
        caso = None
        if dados.caso_id is not None:
            caso = self._caso_ou_erro(dados.caso_id, operador)
            self._pode_editar(caso, operador)
            self._cliente_coerente(caso, dados.cliente_id)
        elif not operador.administrador:
            raise DocumentoSemPermissaoError(
                "Somente o advogado principal pode criar documentos sem caso"
            )

        documento = Documento(
            titulo=dados.titulo.strip(),
            area=dados.area,
            tipo=dados.tipo,
            html=dados.html,
            caso_id=caso.id if caso else None,
            cliente_id=dados.cliente_id,
            pasta_id=dados.pasta_id,
            criado_por=operador.id,
        )
        return self.documentos.criar(documento)

    # -------------------------------------------------------- atualizacao

    def atualizar(
        self, documento_id: int, dados: DocumentoUpdate, operador: Usuario
    ) -> Documento:
        documento = self.buscar(documento_id, operador)
        self._pode_editar_documento(documento, operador)

        campos = dados.model_dump(exclude_unset=True)
        if "titulo" in campos and campos["titulo"] is not None:
            campos["titulo"] = campos["titulo"].strip()

        caso = None
        if "caso_id" in campos:
            novo_id = campos["caso_id"]
            if novo_id is None:
                if not operador.administrador:
                    raise DocumentoSemPermissaoError(
                        "Somente o administrador pode desvincular um documento do caso"
                    )
            else:
                caso = self._caso_ou_erro(novo_id, operador)
                self._pode_editar(caso, operador)
        elif documento.caso_id is not None:
            caso = self._caso_ou_erro(documento.caso_id, operador)

        cliente_id = campos.get("cliente_id", documento.cliente_id)
        if caso is not None:
            self._cliente_coerente(caso, cliente_id)

        for campo, valor in campos.items():
            setattr(documento, campo, valor)
        documento.atualizado_em = utcnow()
        return self.documentos.atualizar(documento)

    def mover(
        self, documento_id: int, dados: DocumentoMover, operador: Usuario
    ) -> Documento:
        """Troca apenas a pasta; nao toca no conteudo nem na data de edicao."""
        documento = self.buscar(documento_id, operador)
        self._pode_editar_documento(documento, operador)

        if documento.caso_id is not None:
            caso = self._caso_ou_erro(documento.caso_id, operador)
            self._cliente_coerente(caso, dados.cliente_id)
        elif not operador.administrador:
            raise DocumentoSemPermissaoError(
                "Somente o administrador pode organizar documentos sem caso"
            )

        documento.cliente_id = dados.cliente_id
        documento.pasta_id = dados.pasta_id
        return self.documentos.atualizar(documento)

    # ------------------------------------------------------------ exclusao

    def excluir(self, documento_id: int, operador: Usuario) -> None:
        documento = self.buscar(documento_id, operador)
        self._pode_editar_documento(documento, operador)
        self.documentos.excluir(documento)

    # ------------------------------------------------------------- privado

    def _caso_ou_erro(self, caso_id: int, usuario: Usuario) -> Caso:
        caso = self.casos.buscar_visivel(caso_id, usuario, incluir_arquivados=True)
        if caso is None:
            raise CasoNaoEncontradoError("Caso nao encontrado")
        return caso

    def _pode_editar(self, caso: Caso, operador: Usuario) -> None:
        if operador.administrador or caso.responsavel_id == operador.id:
            return
        linha = self.permissoes.buscar(operador.id, caso.id)
        if linha is not None and linha.ativo and linha.pode_gerenciar_processos:
            return
        raise DocumentoSemPermissaoError(
            "Sem permissao para gerenciar documentos deste caso"
        )

    def _pode_editar_documento(
        self, documento: Documento, operador: Usuario
    ) -> None:
        if documento.caso_id is None:
            if not operador.administrador:
                raise DocumentoSemPermissaoError(
                    "Somente o administrador pode alterar documentos sem caso"
                )
            return
        self._pode_editar(self._caso_ou_erro(documento.caso_id, operador), operador)

    @staticmethod
    def _cliente_coerente(caso: Caso, cliente_id: int | None) -> None:
        """O cliente da pasta tem que ser o cliente do caso vinculado."""
        if (
            cliente_id is not None
            and caso.cliente_id is not None
            and cliente_id != caso.cliente_id
        ):
            raise DadosInvalidosError(
                "O cliente do documento deve ser o cliente do caso vinculado"
            )


__all__ = [
    "DocumentoService",
    "DocumentoNaoEncontradoError",
    "DocumentoSemPermissaoError",
]
