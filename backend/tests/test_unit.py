"""Testes unitarios: security (bcrypt/JWT), Limiter e Services.

Nao usam FastAPI nem banco - apenas objetos puros.
"""

from datetime import timedelta, timezone
import time

import jwt
import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.core import security
from app.core.ratelimit import Limiter
from app.models.usuario import Perfil, Usuario
from app.services.auth_service import (
    AuthService,
    ErroAutenticacao,
    UsuarioInativoError,
)
from app.services.usuario_service import (
    DadosInvalidosError,
    EmailJaCadastradoError,
    UsuarioService,
)

settings = get_settings()


# --------------------------------------------------------------- bcrypt

class TestSenhas:
    def test_hash_nao_contem_a_senha_pura(self):
        digest = security.hash_senha("Minha@Senha123")
        assert "Minha@Senha123" not in digest
        assert digest.startswith("$2")  # prefixo bcrypt

    def test_verificar_senha_correta(self):
        digest = security.hash_senha("Minha@Senha123")
        assert security.verificar_senha("Minha@Senha123", digest)

    def test_verificar_senha_incorreta(self):
        digest = security.hash_senha("Minha@Senha123")
        assert not security.verificar_senha("SenhaErrada", digest)

    def test_verificar_senha_hash_corrompido_nao_estoura(self):
        assert not security.verificar_senha("qualquer", "nao-e-hash")
        assert not security.verificar_senha("qualquer", "")


# ----------------------------------------------------------------- JWT

class TestToken:
    def test_roundtrip_com_csrf(self):
        token = security.criar_token(subject="1", perfil="ADMIN", csrf="abc123")
        payload = security.decodificar_token(token)
        assert payload["sub"] == "1"
        assert payload["perfil"] == "ADMIN"
        assert payload["csrf"] == "abc123"
        assert "exp" in payload and "iat" in payload

    def test_token_assinatura_falsa_retorna_none(self):
        token = security.criar_token(subject="1", perfil="ADMIN", csrf="x")
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_signature": False},
        )
        payload["sub"] = "999"  # atacante troca o id
        forjado = jwt.encode(payload, "segredo-do-atacante", algorithm="HS256")
        assert security.decodificar_token(forjado) is None

    def test_token_expirado_retorna_none(self):
        from datetime import datetime

        agora = datetime.now(timezone.utc)
        payload = {
            "sub": "1",
            "perfil": "ADMIN",
            "csrf": "x",
            "iat": agora - timedelta(hours=9),
            "exp": agora - timedelta(hours=8),  # ja vencido
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        assert security.decodificar_token(token) is None

    def test_token_lixo_retorna_none(self):
        assert security.decodificar_token("abc.def.ghi") is None
        assert security.decodificar_token("") is None


# ----------------------------------------------------------- rate limit

class TestLimiter:
    def test_permite_ate_o_limite(self):
        limiter = Limiter()
        for _ in range(3):
            limiter.check("ip:1.2.3.4", limite=3, janela=60)

    def test_bloqueia_acima_do_limite_com_429_e_retry_after(self):
        limiter = Limiter()
        for _ in range(2):
            limiter.check("ip:1.2.3.4", limite=2, janela=60)
        with pytest.raises(HTTPException) as exc:
            limiter.check("ip:1.2.3.4", limite=2, janela=60)
        assert exc.value.status_code == 429
        assert exc.value.headers["Retry-After"] == "60"

    def test_chaves_sao_independentes(self):
        limiter = Limiter()
        limiter.check("ip:1.1.1.1", limite=1, janela=60)
        limiter.check("ip:2.2.2.2", limite=1, janela=60)  # nao pode bloquear

    def test_reset_zera_contadores(self):
        limiter = Limiter()
        limiter.check("ip:1.1.1.1", limite=1, janela=60)
        limiter.reset()
        limiter.check("ip:1.1.1.1", limite=1, janela=60)  # de novo livre


# ------------------------------------------------------------- services

class FakeRepo:
    """Repository falso (padrao Fake para unit tests de service)."""

    class _Sessao:
        def rollback(self):
            pass

    def __init__(self, usuarios=None):
        self.usuarios = usuarios or []
        self._proximo_id = len(self.usuarios) + 1
        self.db = self._Sessao()

    def buscar_por_email(self, email):
        return next((u for u in self.usuarios if u.email == email), None)

    def buscar_por_id(self, usuario_id):
        return next((u for u in self.usuarios if u.id == usuario_id), None)

    def listar(self):
        return self.usuarios

    def criar(self, usuario):
        usuario.id = self._proximo_id
        self._proximo_id += 1
        self.usuarios.append(usuario)
        return usuario


def _usuario(senha_digest=None, ativo=True, email="user@jadilson.adv"):
    return Usuario(
        id=1,
        nome="Usuario Teste",
        email=email,
        senha_hash=senha_digest or security.hash_senha("Senha@123"),
        perfil=Perfil.PADRAO.value,
        ativo=ativo,
    )


class TestAuthService:
    def test_autenticar_ok(self):
        usuario = _usuario()
        service = AuthService(FakeRepo([usuario]))
        assert service.autenticar(" USER@JADILSON.ADV ", "Senha@123") is usuario

    def test_autenticar_senha_errada(self):
        service = AuthService(FakeRepo([_usuario()]))
        with pytest.raises(ErroAutenticacao):
            service.autenticar("user@jadilson.adv", "Errada@1")

    def test_autenticar_email_inexistente_mesmo_erro(self):
        """Nao pode revelar se o email existe."""
        service = AuthService(FakeRepo([]))
        with pytest.raises(ErroAutenticacao) as exc:
            service.autenticar("ninguem@jadilson.adv", "Senha@123")
        assert str(exc.value) == "E-mail ou senha invalidos"

    def test_autenticar_inativo(self):
        service = AuthService(FakeRepo([_usuario(ativo=False)]))
        with pytest.raises(UsuarioInativoError):
            service.autenticar("user@jadilson.adv", "Senha@123")

    def test_gerar_sessao_devolve_token_e_csrf(self):
        usuario = _usuario()
        service = AuthService(FakeRepo([usuario]))
        token, csrf = service.gerar_sessao(usuario)
        payload = security.decodificar_token(token)
        assert payload["sub"] == str(usuario.id)
        assert payload["csrf"] == csrf
        assert len(csrf) >= 32

    def test_csrf_diferente_por_sessao(self):
        usuario = _usuario()
        service = AuthService(FakeRepo([usuario]))
        _, csrf1 = service.gerar_sessao(usuario)
        _, csrf2 = service.gerar_sessao(usuario)
        assert csrf1 != csrf2


class TestUsuarioService:
    def test_criar_normaliza_email(self):
        repo = FakeRepo()
        service = UsuarioService(repo)
        service.criar("Nova", " NOVA@Adv.Com.BR ", "Senha@123", "PADRAO")
        assert repo.usuarios[0].email == "nova@adv.com.br"

    def test_criar_email_duplicado(self):
        repo = FakeRepo([_usuario()])
        service = UsuarioService(repo)
        with pytest.raises(EmailJaCadastradoError):
            service.criar("Outro", "user@jadilson.adv", "Senha@123", "PADRAO")

    def test_criar_perfil_invalido(self):
        service = UsuarioService(FakeRepo())
        with pytest.raises(DadosInvalidosError):
            service.criar("X", "x@jadilson.adv", "Senha@123", "SUPER")

    def test_criar_senha_curta(self):
        service = UsuarioService(FakeRepo())
        with pytest.raises(DadosInvalidosError):
            service.criar("X", "x@jadilson.adv", "12345", "PADRAO")

    def test_criar_senha_muito_longa_vira_erro_nao_500(self):
        """bcrypt rejeita >72 bytes; o service deve traduzir para erro de negocio."""
        service = UsuarioService(FakeRepo())
        with pytest.raises(DadosInvalidosError):
            service.criar("X", "x@jadilson.adv", "A" * 200, "PADRAO")

    def test_criar_email_duplicado_por_corrida_vira_erro_de_negocio(self):
        """Se o INSERT falhar por UNIQUE (check-then-insert), vira 409, nao 500."""
        from sqlalchemy.exc import IntegrityError

        class RepoCorrida(FakeRepo):
            def criar(self, usuario):
                raise IntegrityError("INSERT", {}, Exception("dup"))

        service = UsuarioService(RepoCorrida())
        with pytest.raises(EmailJaCadastradoError):
            service.criar("X", "x@jadilson.adv", "Senha@123", "PADRAO")


# ------------------------------------------- enumeracao por timing (login)

class TestAntiEnumeracao:
    def test_rodar_bcrypt_mesmo_quando_email_nao_existe(self, monkeypatch):
        """Sem usuario, ainda deve rodar o bcrypt para igualar o tempo de resposta."""
        chamadas = []

        def espio(senha, senha_hash):
            chamadas.append(senha_hash)
            return False

        monkeypatch.setattr(
            "app.services.auth_service.security.verificar_senha", espio
        )
        service = AuthService(FakeRepo([]))  # nenhum usuario
        with pytest.raises(ErroAutenticacao):
            service.autenticar("fantasma@jadilson.adv", "Senha@123")
        assert len(chamadas) == 1  # bcrypt rodou apesar de nao existir o email


# --------------------------------------------------- revogacao de token (jti)

class TestTokenRevogados:
    def test_revogar_e_detectar(self):
        from app.core.revogados import TokenRevogados

        rev = TokenRevogados()
        assert not rev.esta_revogado("abc")
        rev.revogar("abc", exp=time.time() + 60)
        assert rev.esta_revogado("abc")

    def test_revogar_jti_vazio_e_noop(self):
        from app.core.revogados import TokenRevogados

        rev = TokenRevogados()
        rev.revogar(None)
        assert not rev.esta_revogado(None)

    def test_jti_expirado_nao_conta(self):
        from app.core.revogados import TokenRevogados

        rev = TokenRevogados()
        rev.revogar("velho", exp=time.time() - 1)  # ja vencido
        assert not rev.esta_revogado("velho")

    def test_reset_zera(self):
        from app.core.revogados import TokenRevogados

        rev = TokenRevogados()
        rev.revogar("abc", exp=time.time() + 60)
        rev.reset()
        assert not rev.esta_revogado("abc")


# ------------------------------------------------------- novos metodos Limiter

class TestLimiterMetodosNovos:
    def test_bloqueado_nao_registra(self):
        limiter = Limiter()
        limiter.bloqueado("email:x", limite=1, janela=60)  # so consulta
        limiter.bloqueado("email:x", limite=1, janela=60)  # continua liberado

    def test_bloqueado_levanta_429_no_limite(self):
        limiter = Limiter()
        limiter.registrar("email:x", janela=60)
        with pytest.raises(HTTPException) as exc:
            limiter.bloqueado("email:x", limite=1, janela=60)
        assert exc.value.status_code == 429

    def test_registrar_sem_cheque_depois_bloqueia(self):
        limiter = Limiter()
        for _ in range(3):
            limiter.registrar("email:y", janela=60)
        with pytest.raises(HTTPException):
            limiter.bloqueado("email:y", limite=3, janela=60)

    def test_limpar_zera_bucket(self):
        limiter = Limiter()
        limiter.registrar("email:z", janela=60)
        limiter.limpar("email:z")
        limiter.bloqueado("email:z", limite=1, janela=60)  # nao levanta


# ------------------------------------------------ validacao de config (producao)

class TestValidacaoConfigSeguranca:
    def _settings(self, **kw):
        from app.config import Settings

        base = dict(
            app_env="production",
            jwt_secret="um-segredo-forte-com-mais-de-32-bytes-aleatorios-aqui",
            auth_cookie_secure=True,
            cors_origins=["https://app.exemplo.adv"],
        )
        base.update(kw)
        return Settings(_env_file=None, **base)

    def test_producao_com_config_forte_passa(self):
        from app.config import validar_configuracao_seguranca

        validar_configuracao_seguranca(self._settings())  # nao deve levantar

    def test_producao_com_segredo_padrao_levanta(self):
        from app.config import validar_configuracao_seguranca

        with pytest.raises(RuntimeError):
            validar_configuracao_seguranca(
                self._settings(
                    jwt_secret="troque-este-segredo-por-um-valor-aleatorio"
                )
            )

    def test_producao_com_segredo_curto_levanta(self):
        from app.config import validar_configuracao_seguranca

        with pytest.raises(RuntimeError):
            validar_configuracao_seguranca(self._settings(jwt_secret="curto"))

    def test_producao_com_cookie_insecure_levanta(self):
        from app.config import validar_configuracao_seguranca

        with pytest.raises(RuntimeError):
            validar_configuracao_seguranca(self._settings(auth_cookie_secure=False))

    def test_desenvolvimento_so_avisa_nao_levanta(self):
        from app.config import validar_configuracao_seguranca

        with pytest.warns(UserWarning):
            validar_configuracao_seguranca(
                self._settings(app_env="development", jwt_secret="curto")
            )


# ---------------------------------------------------- claims `sub` validos

class TestSubValido:
    def test_sub_valido_vira_int(self):
        from app.api.deps import _sub_valido

        assert _sub_valido({"sub": "42"}) == 42

    def test_sub_ausente_vira_none(self):
        from app.api.deps import _sub_valido

        assert _sub_valido({}) is None

    def test_sub_nao_numerico_vira_none(self):
        from app.api.deps import _sub_valido

        assert _sub_valido({"sub": "abc"}) is None
