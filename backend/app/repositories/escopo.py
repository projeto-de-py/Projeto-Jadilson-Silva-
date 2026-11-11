"""Escopo de acesso: fonte unica da regra de visibilidade por usuario (Fases 1-3).

Regras:
- advogado principal (`administrador`): enxerga todos os casos e clientes;
- advogado colaborador e funcionario: somente os casos com concessao ativa em
  `usuario_casos` (com `pode_visualizar`) - e tudo o que deriva deles, como
  prazos, clientes e processos judiciais.

Toda consulta de leitura (casos, prazos, clientes e processos) deve passar por
estas condicoes para que a autorizacao nao fique espalhada pela aplicacao.
"""

from sqlalchemy import Select, and_, select, true
from sqlalchemy.sql.elements import ColumnElement

from app.models.caso import Caso
from app.models.cliente import Cliente
from app.models.compromisso import Compromisso
from app.models.prazo import Prazo
from app.models.processo_judicial import ProcessoJudicial
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


def condicao_processo_visivel(usuario: Usuario) -> ColumnElement[bool]:
    """Processos de casos que o usuario pode acessar (herda o escopo do caso).

    Um processo nunca da acesso indireto a um caso nao autorizado: quem nao
    ve o caso nao ve os processos dele.
    """
    if usuario.administrador:
        return true()
    return ProcessoJudicial.caso_id.in_(casos_autorizados(usuario))


def condicao_compromisso_visivel(usuario: Usuario) -> ColumnElement[bool]:
    """Compromissos que o usuario pode enxergar (Fase 4).

    - compromissos COM caso: herdam o escopo do caso (Fase 1);
    - compromissos SEM caso: nao pertencem a nenhuma demanda, entao somente o
      administrador os enxerga (a agenda nunca fica publica).
    """
    if usuario.administrador:
        return true()
    return and_(
        Compromisso.caso_id.is_not(None),
        Compromisso.caso_id.in_(casos_autorizados(usuario)),
    )


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
