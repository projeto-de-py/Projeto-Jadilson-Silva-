"""Escopo de acesso: fonte unica da regra de visibilidade por usuario (Fase 1).

Regras:
- advogado principal (`administrador`): enxerga todos os casos e clientes;
- advogado colaborador e funcionario: somente os casos com concessao ativa em
  `usuario_casos` (com `pode_visualizar`) - e tudo o que deriva deles, como
  prazos e clientes.

Toda consulta de leitura (casos, prazos e clientes) deve passar por estas
condicoes para que a autorizacao nao fique espalhada pela aplicacao.
"""

from sqlalchemy import Select, select, true
from sqlalchemy.sql.elements import ColumnElement

from app.models.caso import Caso
from app.models.cliente import Cliente
from app.models.prazo import Prazo
from app.models.usuario import Usuario
from app.models.usuario_caso import UsuarioCaso


def casos_autorizados(usuario: Usuario) -> Select:
    """Subconsulta com os ids de caso que o usuario pode efetivamente ver."""
    return select(UsuarioCaso.caso_id).where(
        UsuarioCaso.usuario_id == usuario.id,
        UsuarioCaso.ativo.is_(True),
        UsuarioCaso.pode_visualizar.is_(True),
    )


def condicao_caso_visivel(usuario: Usuario) -> ColumnElement[bool]:
    if usuario.administrador:
        return true()
    return Caso.id.in_(casos_autorizados(usuario))


def condicao_prazo_visivel(usuario: Usuario) -> ColumnElement[bool]:
    if usuario.administrador:
        return true()
    return Prazo.caso_id.in_(casos_autorizados(usuario))


def condicao_cliente_visivel(usuario: Usuario) -> ColumnElement[bool]:
    """Clientes vinculados a casos que o usuario pode acessar."""
    if usuario.administrador:
        return true()
    return Cliente.id.in_(
        select(Caso.cliente_id).where(
            Caso.cliente_id.is_not(None),
            Caso.id.in_(casos_autorizados(usuario)),
        )
    )
