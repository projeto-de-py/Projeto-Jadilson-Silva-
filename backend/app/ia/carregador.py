"""Le os perfis e as tarefas (arquivos .md) que definem o comportamento da IA.

Os textos ficam em `perfis/` e `tarefas/`, versionados no git: quem ajusta o
comportamento da IA edita esses arquivos, sem tocar em codigo. Cada resposta
guarda a `versao` (hash curto do conteudo usado) para auditoria.
"""

from functools import lru_cache
from hashlib import sha256
from pathlib import Path

from app.ia.schemas import AreaIA, TarefaIA

BASE = Path(__file__).resolve().parent
PERFIS = BASE / "perfis"
EXEMPLOS = BASE / "exemplos"
TAREFAS = BASE / "tarefas"

_ARQUIVO_AREA = {
    AreaIA.TRABALHISTA: "trabalhista.md",
    AreaIA.BANCARIO: "bancario.md",
    AreaIA.PREVIDENCIARIO: "previdenciario.md",
}


@lru_cache(maxsize=None)
def _ler(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8").strip()


def limpar_cache() -> None:
    """Forca reler os arquivos (usado em testes e apos editar um prompt)."""
    _ler.cache_clear()


def instrucoes_sistema(area: AreaIA | None) -> str:
    """Perfil do redator juridico + perfil da area (quando houver)."""
    partes = [_ler(PERFIS / "redator_juridico.md")]
    arquivo = _ARQUIVO_AREA.get(area) if area else None
    if arquivo:
        partes.append(_ler(PERFIS / arquivo))
        exemplo = EXEMPLOS / arquivo  # few-shot da materia, se existir
        if exemplo.exists():
            partes.append(_ler(exemplo))
    return "\n\n---\n\n".join(partes)


def instrucoes_tarefa(tarefa: TarefaIA | str) -> str:
    """Instrucao da tarefa + formato de resposta obrigatorio."""
    nome = tarefa.value if isinstance(tarefa, TarefaIA) else tarefa
    corpo = _ler(TAREFAS / f"{nome}.md")
    if nome == "completar":
        return corpo  # o autocompletar responde texto puro, sem JSON
    return corpo + "\n\n---\n\n" + _ler(TAREFAS / "_formato_resposta.md")


def versao(area: AreaIA | None, tarefa: TarefaIA | str) -> str:
    """Hash curto do conjunto de prompts usado (auditoria)."""
    conteudo = instrucoes_sistema(area) + instrucoes_tarefa(tarefa)
    return sha256(conteudo.encode("utf-8")).hexdigest()[:12]


def _descrever(pasta: Path) -> list[dict]:
    itens = []
    for arq in sorted(pasta.glob("*.md")):
        texto = arq.read_text(encoding="utf-8")
        itens.append(
            {
                "nome": arq.name,
                "tamanho": len(texto.encode("utf-8")),
                "versao": sha256(texto.encode("utf-8")).hexdigest()[:12],
            }
        )
    return itens


def inventario() -> dict[str, list[dict]]:
    """Lista os arquivos de controle (nome, tamanho, versao) - sem expor o conteudo."""
    return {"perfis": _descrever(PERFIS), "tarefas": _descrever(TAREFAS), "exemplos": _descrever(EXEMPLOS)}
