"""Clientes: consulta por escopo de acesso, cadastro, edicao e remocao (Admin).

Um usuario comum so enxerga os clientes dos casos aos quais tem acesso; a
listagem geral, cadastro, edicao e remocao sao restritos ao advogado principal.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status as http_status,
)

from app.api.deps import (
    get_cliente_repo,
    get_current_user,
    require_admin,
)
from app.core.validacao import DocumentoInvalidoError, TelefoneInvalidoError
from app.models.cliente import Cliente
from app.models.usuario import Usuario
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.notificacao_repository import NotificacaoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.cliente import (
    ClienteCreate,
    ClienteOut,
    ClientePaginaOut,
    ClienteUpdate,
)
from app.services.cliente_service import (
    ClienteNaoEncontradoError,
    ClienteService,
    DadosInvalidosError,
    DocumentoJaCadastradoError,
)
from app.services.notificacao_service import (
    GeradorNotificacaoCliente,
    NotificacaoService,
)

router = APIRouter()


@router.get(
    "",
    response_model=ClientePaginaOut,
    summary="Listar clientes (escopo do usuario autenticado)",
)
def listar_clientes(
    q: str | None = Query(None, min_length=1, max_length=160),
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    _usuario: Usuario = Depends(get_current_user),
    repo: ClienteRepository = Depends(get_cliente_repo),
):
    return ClienteService(repo).listar(
        _usuario, q=q, pagina=pagina, limite=limite
    )


@router.post(
    "",
    response_model=ClienteOut,
    status_code=http_status.HTTP_201_CREATED,
    summary="Cadastrar cliente (Admin)",
)
def criar_cliente(
    dados: ClienteCreate,
    _admin: Usuario = Depends(require_admin),
    repo: ClienteRepository = Depends(get_cliente_repo),
) -> Cliente:
    try:
        cliente = ClienteService(repo).criar(
            nome=dados.nome,
            cpf_cnpj=dados.cpf_cnpj,
            email=dados.email,
            telefone=dados.telefone,
            data_nascimento=dados.data_nascimento,
        )
        ids_ativos = [
            u.id for u in UsuarioRepository(repo.db).listar() if u.ativo
        ]
        GeradorNotificacaoCliente(
            NotificacaoService(NotificacaoRepository(repo.db))
        ).cadastrado(ids_ativos, cliente.id)
        return cliente
    except DocumentoInvalidoError as exc:
        raise HTTPException(
            http_status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)
        )
    except TelefoneInvalidoError as exc:
        raise HTTPException(
            http_status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)
        )
    except DadosInvalidosError as exc:
        raise HTTPException(
            http_status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)
        )
    except DocumentoJaCadastradoError as exc:
        raise HTTPException(http_status.HTTP_409_CONFLICT, str(exc))


@router.get(
    "/{cliente_id}",
    response_model=ClienteOut,
    summary="Detalhe do cliente (404 fora do escopo)",
)
def buscar_cliente(
    cliente_id: int,
    _usuario: Usuario = Depends(get_current_user),
    repo: ClienteRepository = Depends(get_cliente_repo),
) -> Cliente:
    try:
        return ClienteService(repo).buscar(cliente_id, _usuario)
    except ClienteNaoEncontradoError as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))


@router.put(
    "/{cliente_id}",
    response_model=ClienteOut,
    summary="Editar cliente (Admin)",
)
def editar_cliente(
    cliente_id: int,
    dados: ClienteUpdate,
    _admin: Usuario = Depends(require_admin),
    repo: ClienteRepository = Depends(get_cliente_repo),
) -> Cliente:
    try:
        return ClienteService(repo).atualizar(
            cliente_id=cliente_id,
            nome=dados.nome,
            cpf_cnpj=dados.cpf_cnpj,
            email=dados.email,
            telefone=dados.telefone,
            data_nascimento=dados.data_nascimento,
            ativo=dados.ativo,
        )
    except ClienteNaoEncontradoError as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))
    except (
        DocumentoInvalidoError,
        TelefoneInvalidoError,
        DadosInvalidosError,
    ) as exc:
        raise HTTPException(
            http_status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)
        )
    except DocumentoJaCadastradoError as exc:
        raise HTTPException(http_status.HTTP_409_CONFLICT, str(exc))


@router.delete(
    "/{cliente_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Remover cliente (Admin)",
)
def remover_cliente(
    cliente_id: int,
    _admin: Usuario = Depends(require_admin),
    repo: ClienteRepository = Depends(get_cliente_repo),
) -> Response:
    try:
        ClienteService(repo).remover(cliente_id, _admin)
    except ClienteNaoEncontradoError as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
