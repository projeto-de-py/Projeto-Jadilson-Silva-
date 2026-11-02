"""Guardrails de ENTRADA: o que pode ir para a IA e o que deve ser mascarado.

Tres cuidados:
1. Injecao de prompt: instrucoes escondidas no pedido ou em documentos
   enviados ("ignore as regras anteriores"). Documento e DADO, nunca comando.
2. Discurso de odio e ameaca: nao e produzido pela IA. No pedido, bloqueia;
   no texto do advogado, vira um aviso de tom (a revisao propoe redacao objetiva).
3. Dados pessoais: CPF, CNPJ, e-mail e telefone sao mascarados antes de sair
   para qualquer provedor externo (LGPD: enviar so o necessario).
"""

import re
import unicodedata
from dataclasses import dataclass, field


def normalizar(texto: str) -> str:
    """Minusculas, sem acento e com espacos colapsados (para casar padroes)."""
    sem_acento = unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento.lower()).strip()


# ---------------------------------------------------------------- injecao

_INJECAO = [
    r"ignor\w* (todas? )?(as |os )?(instruco\w*|regras|orientaco\w*) (anteriores|acima|do sistema)",
    r"desconsider\w* (todas? )?(as |os )?(instruco\w*|regras)",
    r"(revel\w*|mostr\w*|exib\w*|repit\w*) (o |as |seu |suas )?(prompt|instruco\w*) (do sistema|inicia\w*|internas?)",
    r"\bsystem prompt\b",
    r"ignore (all |any |the )?(previous |prior |above )?(instructions|rules)",
    r"you are now\b",
    r"\bfinja (que )?(voce )?(nao tem|e outra|e um)",
    r"\bmodo (desenvolvedor|deus|sem restricoes)\b",
]
_RE_INJECAO = [re.compile(p) for p in _INJECAO]


def detectar_injecao(texto: str) -> bool:
    n = normalizar(texto)
    return any(r.search(n) for r in _RE_INJECAO)


# ------------------------------------------------------------ odio e ameaca

# Grupos protegidos por categoria ampla. A detecao e por padrao (generalizacao
# + termo degradante), sem depender de uma lista de xingamentos.
_GRUPOS = (
    "negros|brancos|pretos|indigenas|gays|homossexuais|lesbicas|travestis|transexuais|"
    "judeus|muculmanos|evangelicos|catolicos|nordestinos|nortistas|imigrantes|estrangeiros|"
    "mulheres|homens|idosos|velhos|deficientes|cadeirantes|pobres"
)
_DEGRADANTE = (
    "lixo|animais|bichos|inferiores|burros|retardados|vagabundos|nojentos|doentes|"
    "imundos|parasitas|escoria|ladroes|bandidos|vermes|pragas"
)
_ODIO = [
    rf"\b(todos? os |todas as |essa gente de |esses )?({_GRUPOS}) (sao|e|seriam|eram) (todos |todas |sempre |apenas )?({_DEGRADANTE})\b",
    rf"\b({_GRUPOS}) (nao prestam|nao valem nada|deviam sumir|deveriam sumir)\b",
    rf"\b({_GRUPOS}) (merecem|devem|deveriam) (morrer|ser (mortos|exterminados|eliminados|espancados))\b",
    r"\b(vou|vamos|iremos) (te |lhe |os |as )?(matar|espancar|exterminar|eliminar)\b",
    r"\b(merece|merecem) (morrer|sofrer|apanhar)\b",
]
_RE_ODIO = [re.compile(p) for p in _ODIO]

# Ofensa pessoal comum (nao e discurso de odio): vira aviso de tom, nunca bloqueio,
# porque pode estar em citacao legitima de prova.
_OFENSAS = (
    "idiota|imbecil|estupido|canalha|safado|picareta|cretino|vagabundo|desgracado|"
    "miseravel|incompetente|vigarista|ordinario|nojento"
)
_RE_OFENSA = re.compile(rf"\b({_OFENSAS})s?\b")


def detectar_odio(texto: str) -> bool:
    n = normalizar(texto)
    return any(r.search(n) for r in _RE_ODIO)


def trechos_ofensivos(texto: str) -> list[str]:
    """Trechos com ofensa pessoal (para a revisao de tom). Ate 5, com contexto curto."""
    achados = []
    for m in _RE_OFENSA.finditer(normalizar(texto)):
        achados.append(m.group(0))
        if len(achados) == 5:
            break
    return achados


# ------------------------------------------------- palavrao e giria de palavrao

# Palavroes, girias e siglas de xingamento. Casam tambem com letras repetidas
# ("porraaa"), numeros no lugar de letras ("p0rra", "c4ralho") e acentos.
_PALAVROES = (
    "porra|caralho|karalho|krl|crl|merda|bosta|cacete|foda|fode|foder|fodido|fodida|fdp|"
    "puta|puto|putaria|arrombado|arrombada|cuzao|buceta|boceta|pqp|vsf|vtnc|tnc|tmnc|kct|"
    "babaca|otario|otaria|trouxa|desgraca|desgracado|corno|piranha|vagabunda|safada|"
    "cuzinho|punheta|xereca|xota|pau no cu|vai se foder|vai tomar no cu|filho da puta|"
    "fi?lho d[ae] uma puta|cacete"
)

_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s", "!": "i"})


def _tornar_flexivel(palavra: str) -> str:
    """'porra' -> 'p+o+r+a+' (aceita letras repetidas). Expressoes com espaco ficam como estao."""
    if any(c in palavra for c in " ?[]"):
        return palavra
    return "".join(f"{c}+" for c in palavra)


_RE_PALAVRAO = re.compile(r"(?<![a-z])(" + "|".join(_tornar_flexivel(p) for p in _PALAVROES.split("|")) + r")(?![a-z])")


def _sem_disfarce(texto: str) -> str:
    """Normaliza e desfaz disfarces comuns: numeros no lugar de letras e asterisco/ponto no meio."""
    n = normalizar(texto).translate(_LEET)
    return re.sub(r"(?<=[a-z])[*#._-](?=[a-z])", "", n)


def detectar_palavrao(texto: str) -> bool:
    return bool(_RE_PALAVRAO.search(_sem_disfarce(texto)))


def palavroes_encontrados(texto: str) -> list[str]:
    achados = []
    for m in _RE_PALAVRAO.finditer(_sem_disfarce(texto)):
        achados.append(m.group(0))
        if len(achados) == 5:
            break
    return achados


# ------------------------------------------------------------ dados pessoais

_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b")
_CNPJ = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b|\b\d{14}\b")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
_FONE = re.compile(r"(?<!\d)(\(?\d{2}\)?\s?)?9?\d{4}[-\s]?\d{4}(?!\d)")


def mascarar_pii(texto: str) -> str:
    """Troca CPF, CNPJ, e-mail e telefone por marcadores (nada sai para o provedor)."""
    texto = _CNPJ.sub("[CNPJ]", texto)
    texto = _CPF.sub("[CPF]", texto)
    texto = _EMAIL.sub("[E-MAIL]", texto)
    return _FONE.sub("[TELEFONE]", texto)


# ----------------------------------------------------------------- resultado

@dataclass
class ResultadoEntrada:
    bloqueado: bool = False
    motivo: str | None = None
    avisos: list[str] = field(default_factory=list)


def analisar_entrada(pedido: str, texto_documento: str = "") -> ResultadoEntrada:
    """Decide se o pedido segue e quais avisos acompanham a resposta."""
    if detectar_odio(pedido):
        return ResultadoEntrada(
            bloqueado=True,
            motivo=(
                "O pedido contém discurso de ódio ou ameaça, que a IA não redige. "
                "Reformule com os fatos e fundamentos objetivos do caso."
            ),
        )
    if detectar_palavrao(pedido):
        return ResultadoEntrada(
            bloqueado=True,
            motivo=(
                "O pedido contém palavrões ou xingamentos. A IA trabalha com linguagem formal: "
                "reescreva o pedido com termos objetivos e tente de novo."
            ),
        )
    avisos: list[str] = []
    if detectar_injecao(pedido):
        return ResultadoEntrada(
            bloqueado=True,
            motivo="O pedido tenta alterar as regras da IA e foi recusado. Descreva apenas o que precisa ser redigido.",
        )
    if detectar_injecao(texto_documento):
        avisos.append(
            "O documento contém trechos que parecem instruções para a IA. "
            "Eles foram tratados apenas como texto, não como comandos."
        )
    return ResultadoEntrada(avisos=avisos)
