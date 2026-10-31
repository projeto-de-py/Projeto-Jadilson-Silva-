"""Schemas (DTOs) de permissoes de acesso a caso (Usuario <-> Caso)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.usuario import UsuarioOut


class PermissaoCasoCreate(BaseModel):
    """Concessao de acesso de um usuario a um caso (apenas advogado principal).

    Os permissoes de escrita partem desativadas (menor privilegio): podem ser
    ampliadas em etapas futuras, quando o escritorio definir as regras.
    `pode_visualizar=False` nao faz sentido como concessao, por isso e rejeitado.
    """

    model_config = ConfigDict(extra="forbid")

    usuario_id: int = Field(gt=0)
    pode_visualizar: bool = True
    pode_registrar_andamento: bool = False
    pode_gerenciar_prazos: bool = False


class PermissaoCasoOut(BaseModel):
    """Autorizacao de um usuario a um caso (inclusive linhas revogadas)."""

    model_config = ConfigDict(from_attributes=True)

    usuario: UsuarioOut
    pode_visualizar: bool
    pode_registrar_andamento: bool
    pode_gerenciar_prazos: bool
    ativo: bool
    concedido_por: int | None
    concedido_em: datetime
    revogado_por: int | None
    revogado_em: datetime | None
