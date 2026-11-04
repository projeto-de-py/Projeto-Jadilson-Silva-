"""Testes unitarios da validacao de dados cadastrais (CPF, CNPJ, telefone).

Nao usam FastAPI nem banco - apenas funcoes puras de app/core/validacao.py.
"""

import pytest

from app.core.validacao import (
    DocumentoInvalidoError,
    TelefoneInvalidoError,
    digitos,
    eh_cnpj,
    eh_cpf,
    formatar_documento,
    normalizar_documento,
    normalizar_telefone,
)

CPF_VALIDO = "12345678909"          # 123.456.789-09
CNPJ_VALIDO = "11222333000181"      # 11.222.333/0001-81


class TestDigitos:
    def test_remove_tudo_que_nao_for_digito(self):
        assert digitos("(11) 99999-0000") == "11999990000"

    def test_none_vira_string_vazia(self):
        assert digitos(None) == ""


class TestEhCpf:
    def test_cpf_valido(self):
        assert eh_cpf(CPF_VALIDO) is True
        assert eh_cpf("52998224725") is True

    def test_digito_verificador_errado(self):
        assert eh_cpf("12345678900") is False
        assert eh_cpf("52998224724") is False

    def test_todos_digitos_iguais(self):
        assert eh_cpf("11111111111") is False
        assert eh_cpf("00000000000") is False

    def test_tamanho_errado(self):
        assert eh_cpf("1234567890") is False
        assert eh_cpf("123456789012") is False

    def test_conteudo_nao_numerico(self):
        assert eh_cpf("abcdefghijk") is False


class TestEhCnpj:
    def test_cnpj_valido(self):
        assert eh_cnpj(CNPJ_VALIDO) is True
        assert eh_cnpj("00000000000191") is True

    def test_digito_verificador_errado(self):
        assert eh_cnpj("11222333000180") is False
        assert eh_cnpj("12345678000199") is False

    def test_todos_digitos_iguais(self):
        assert eh_cnpj("11111111111111") is False

    def test_tamanho_errado(self):
        assert eh_cnpj("1122233300018") is False  # 13 digitos


class TestNormalizarDocumento:
    def test_remove_formatacao(self):
        assert normalizar_documento("123.456.789-09") == CPF_VALIDO
        assert normalizar_documento("11.222.333/0001-81") == CNPJ_VALIDO

    def test_ausente_vira_none(self):
        assert normalizar_documento(None) is None
        assert normalizar_documento("") is None
        assert normalizar_documento("   ") is None

    def test_quantidade_errada(self):
        with pytest.raises(DocumentoInvalidoError):
            normalizar_documento("1234567890")

    def test_caracter_invalido(self):
        with pytest.raises(DocumentoInvalidoError):
            normalizar_documento("1234567890A")

    def test_digitos_verificadores_invalidos(self):
        with pytest.raises(DocumentoInvalidoError):
            normalizar_documento("111.111.111-11")


class TestFormatarDocumento:
    def test_formata_cpf_e_cnpj(self):
        assert formatar_documento(CPF_VALIDO) == "123.456.789-09"
        assert formatar_documento(CNPJ_VALIDO) == "11.222.333/0001-81"

    def test_ausente_vira_none(self):
        assert formatar_documento(None) is None
        assert formatar_documento("") is None


class TestNormalizarTelefone:
    def test_remove_mascara(self):
        assert normalizar_telefone("(11) 99999-0000") == "11999990000"
        assert normalizar_telefone("+55 11 99999-0000") == "5511999990000"

    def test_somente_digitos(self):
        assert normalizar_telefone("11999990000") == "11999990000"

    def test_ausente_vira_none(self):
        assert normalizar_telefone(None) is None
        assert normalizar_telefone("") is None

    def test_com_letras_rejeitado(self):
        with pytest.raises(TelefoneInvalidoError):
            normalizar_telefone("ligue-me")

    def test_curto_demais(self):
        with pytest.raises(TelefoneInvalidoError):
            normalizar_telefone("1234567")

    def test_comprimento_aceito(self):
        assert normalizar_telefone("(11) 3456-7890") == "1134567890"
