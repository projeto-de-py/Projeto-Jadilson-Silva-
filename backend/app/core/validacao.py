"""Validacao e normalizacao de dados cadastrais (CPF, CNPJ, telefone e CNJ).

Regras de negocio aplicadas pelos services; os erros levantados aqui sao
traduzidos para HTTP 422 na camada de rota.
"""

import re

# Caracteres de formatacao aceitos em documentos/telefones (pontos, tracos etc.)
_FORMATACAO = re.compile(r"[.\-/\s()]")
_NAO_DIGITOS = re.compile(r"\D")


class DocumentoInvalidoError(ValueError):
    """CPF/CNPJ com formato ou digitos verificadores invalidos."""


class TelefoneInvalidoError(ValueError):
    """Telefone fora do formato aceito (DDD + numero)."""


# --------------------------------------------------------------- digitos

def digitos(valor: str | None) -> str:
    """Remove tudo o que nao for digito."""
    return _NAO_DIGITOS.sub("", valor or "")


# ------------------------------------------------------------ CPF / CNPJ

def _digito_verificador(base: list[int], pesos: list[int] | range) -> int:
    soma = sum(n * peso for n, peso in zip(base, pesos))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def eh_cpf(cpf: str) -> bool:
    """Confere os dois digitos verificadores do CPF (ja normalizado)."""
    if len(cpf) != 11 or not cpf.isdigit() or len(set(cpf)) == 1:
        return False
    nums = [int(c) for c in cpf]
    d1 = _digito_verificador(nums[:9], range(10, 1, -1))
    d2 = _digito_verificador(nums[:9] + [d1], range(11, 1, -1))
    return nums[9] == d1 and nums[10] == d2


def eh_cnpj(cnpj: str) -> bool:
    """Confere os dois digitos verificadores do CNPJ (ja normalizado)."""
    if len(cnpj) != 14 or not cnpj.isdigit() or len(set(cnpj)) == 1:
        return False
    nums = [int(c) for c in cnpj]
    d1 = _digito_verificador(nums[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = _digito_verificador(nums[:12] + [d1], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return nums[12] == d1 and nums[13] == d2


def normalizar_documento(valor: str | None) -> str | None:
    """Devolve apenas os digitos do CPF (11) ou CNPJ (14), ou None se ausente.

    Politica para documento ausente: valor nulo/vazio vira None. Como a coluna
    e anulavel e o UNIQUE do banco ignora NULL, varios clientes podem ficar sem
    documento - a unicidade so e aplicada a documentos presentes.
    """
    if valor is None:
        return None
    bruto = str(valor).strip()
    if not bruto:
        return None
    limpo = _FORMATACAO.sub("", bruto)
    if not limpo.isdigit():
        raise DocumentoInvalidoError("Documento deve conter apenas digitos (CPF ou CNPJ)")
    if len(limpo) not in (11, 14):
        raise DocumentoInvalidoError("Documento deve ter 11 digitos (CPF) ou 14 digitos (CNPJ)")
    if len(set(limpo)) == 1:
        raise DocumentoInvalidoError("Documento invalido")
    valido = eh_cpf(limpo) if len(limpo) == 11 else eh_cnpj(limpo)
    if not valido:
        raise DocumentoInvalidoError("CPF/CNPJ invalido (digitos verificadores nao conferem)")
    return limpo


def formatar_documento(valor: str | None) -> str | None:
    """Formata para exibicao: 12345678909 -> 123.456.789-09."""
    if not valor:
        return None
    if len(valor) == 11:
        return f"{valor[:3]}.{valor[3:6]}.{valor[6:9]}-{valor[9:]}"
    if len(valor) == 14:
        return f"{valor[:2]}.{valor[2:5]}.{valor[5:8]}/{valor[8:12]}-{valor[12:]}"
    return valor


# --------------------------------------------------------------- telefone

# Formatacoes aceitas na entrada: (11) 99999-9999, +55 11 ..., etc.
# Letras e outros simbolos continuam sendo rejeitados.
_FORMATACAO_FONE = re.compile(r"^[0-9\s()+.\-]+$")


def normalizar_telefone(valor: str | None) -> str | None:
    """Devolve apenas os digitos (10 a 15) ou None quando ausente.

    Aceita a formatacao comum ((11) 99999-9999, +55 11 ...) e guarda somente
    os digitos, para a busca e a exibicao nao dependerem da mascara.
    """
    if valor is None:
        return None
    bruto = str(valor).strip()
    if not bruto:
        return None
    if not _FORMATACAO_FONE.fullmatch(bruto):
        raise TelefoneInvalidoError("Telefone invalido (informe DDD + numero)")
    apenas = digitos(bruto)
    if not 10 <= len(apenas) <= 15:
        raise TelefoneInvalidoError("Telefone deve ter entre 10 e 15 digitos")
    return apenas


# ----------------------------------------------------------- numero CNJ

class NumeroProcessoInvalidoError(ValueError):
    """Numero de processo fora do padrao CNJ (tamanho ou digitos verificadores)."""


def eh_cnj(numero: str | None) -> bool:
    """Confere o digito verificador do padrao CNJ (numero ja normalizado).

    O numero CNJ tem 20 digitos: NNNNNNN-DD.AAAA.J.TR.OOOO. O digito
    verificador (DD) e valido quando o numero COMPLETO interpretado como
    inteiro tem resto 1 na divisao por 97 (algoritmo modulo 97 do padrao CNJ,
    nao apenas expressao regular).
    """
    if numero is None or len(numero) != 20 or not numero.isdigit():
        return False
    if len(set(numero)) == 1:  # todos os digitos iguais nunca sao validos
        return False
    return int(numero) % 97 == 1


def normalizar_numero_processo(valor: str | None) -> str | None:
    """Normaliza um numero CNJ para os 20 digitos, validando os verificadores.

    Aceita a formatacao comum (0001234-56.2025.8.26.0100) ou apenas digitos;
    devolve somente os 20 digitos (consistente com a politica de CPF/CNPJ,
    guardados sem mascara). Numero ausente/vazio devolve None.
    """
    if valor is None:
        return None
    bruto = str(valor).strip()
    if not bruto:
        return None
    apenas = digitos(bruto)
    if len(apenas) != 20:
        raise NumeroProcessoInvalidoError(
            "Numero de processo deve ter 20 digitos (padrao CNJ)"
        )
    if not eh_cnj(apenas):
        raise NumeroProcessoInvalidoError(
            "Numero de processo invalido (digitos verificadores nao conferem)"
        )
    return apenas


def formatar_numero_processo(valor: str | None) -> str | None:
    """Formata para exibicao: 20 digitos -> 0001234-56.2025.8.26.0100."""
    if not valor or len(valor) != 20:
        return valor
    return (
        f"{valor[:7]}-{valor[7:9]}.{valor[9:13]}.{valor[13]}."
        f"{valor[14:16]}.{valor[16:20]}"
    )
