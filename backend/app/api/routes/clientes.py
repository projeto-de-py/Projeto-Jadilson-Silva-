"""Clientes: consulta por escopo de acesso e cadastro (Admin).

Um usuario comum so enxerga os clientes dos casos aos quais tem acesso; a
listagem geral e restrita ao advogado principal.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status

from app.api.deps import (
    get_cliente_repo,
    get_current_user,
    require_admin,
)
from app.core.validacao import DocumentoInvalidoError, TelefoneInvalidoError
from app.models.cliente import Cliente
from app.models.usuario import Usuario
from app.repositories.cliente_repository import ClienteRepository
from app.schemas.cliente import ClienteCreate, ClienteOut, ClientePaginaOut
from app.services.cliente_service import (
    ClienteNaoEncontradoError,
    ClienteService,
    DadosInvalidosError,
    DocumentoJaCadastradoError,
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
    return ClienteService(repo).listar(_usuario, q=q, pagina=pagina, limite=limite)


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
        return ClienteService(repo).criar(
            nome=dados.nome,
            cpf_cnpj=dados.cpf_cnpj,
            email=dados.email,
            telefone=dados.telefone,
            data_nascimento=dados.data_nascimento,
        )
    except DocumentoInvalidoError as exc:
        raise HTTPException(http_status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    except TelefoneInvalidoError as exc:
        raise HTTPException(http_status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    except DadosInvalidosError as exc:
        raise HTTPException(http_status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    except DocumentoJaCadastradoError as exc:
        raise HTTPException(http_status.HTTP_409_CONFLICT, str(exc))


@router.get("/{cliente_id}", response_model=ClienteOut, summary="Detalhe do cliente (404 fora do escopo)")
def buscar_cliente(
    cliente_id: int,
    _usuario: Usuario = Depends(get_current_user),
    repo: ClienteRepository = Depends(get_cliente_repo),
) -> Cliente:
    try:
        return ClienteService(repo).buscar(cliente_id, _usuario)
    except ClienteNaoEncontradoError as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))
