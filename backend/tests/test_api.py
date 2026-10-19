"""Testes de API (integration leve com SQLite em memoria).

Cobrem: login (RF01), cookie HttpOnly, CSRF, rate limit, /me, logout e
autorizacao Admin (RF02).
"""

from tests.conftest import ADMIN, PADRAO

CSRF_HEADER = "X-CSRF-Token"


# --------------------------------------------------------------- login

class TestLogin:
    def test_login_ok_devolve_usuario_e_csrf_sem_expor_token(self, client, admin):
        resp = client.post(
            "/api/auth/login", json={"email": ADMIN["email"], "senha": ADMIN["senha"]}
        )
        assert resp.status_code == 200
        corpo = resp.json()
        assert corpo["usuario"]["email"] == ADMIN["email"]
        assert corpo["usuario"]["perfil"] == "ADMIN"
        assert len(corpo["csrf_token"]) >= 32
        # O JWT nao pode aparecer no corpo (vai so no cookie)
        assert "access_token" not in corpo
        assert "token" not in corpo

    def test_login_seta_cookie_httponly_e_samesite(self, client, admin):
        resp = client.post(
            "/api/auth/login", json={"email": ADMIN["email"], "senha": ADMIN["senha"]}
        )
        cookies = resp.headers.get_list("set-cookie")
        session_cookie = next(c for c in cookies if "jadilson_token=" in c)
        assert "HttpOnly" in session_cookie
        assert "SameSite=lax" in session_cookie
        assert "Path=/" in session_cookie
        assert "Secure" not in session_cookie  # dev (em prod seria True)

    def test_login_senha_errada_401_mensagem_generica(self, client, admin):
        resp = client.post(
            "/api/auth/login", json={"email": ADMIN["email"], "senha": "Errada@1"}
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "E-mail ou senha invalidos"

    def test_login_email_inexistente_mesma_mensagem(self, client):
        """Nao pode dar dica de que o email nao existe."""
        resp = client.post(
            "/api/auth/login", json={"email": "fantasma@x.adv", "senha": "Senha@123"}
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "E-mail ou senha invalidos"

    def test_login_inativo_403(self, client, advogada, db_session):
        advogada.ativo = False
        db_session.commit()
        resp = client.post(
            "/api/auth/login", json={"email": PADRAO["email"], "senha": PADRAO["senha"]}
        )
        assert resp.status_code == 403
        assert "inativo" in resp.json()["detail"].lower()

    def test_login_body_invalido_422(self, client):
        resp = client.post(
            "/api/auth/login", json={"email": "nao-e-email", "senha": "123"}
        )
        assert resp.status_code == 422


# ------------------------------------------------------- sessao (/me)

class TestSessao:
    def test_me_sem_cookie_401(self, client):
        assert client.get("/api/auth/me").status_code == 401

    def test_me_com_cookie_ok_e_devolve_csrf(self, client, fazer_login, admin):
        dados = fazer_login(ADMIN["email"], ADMIN["senha"])
        resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        assert resp.json()["usuario"]["email"] == ADMIN["email"]
        assert resp.json()["csrf_token"] == dados["csrf_token"]

    def test_me_com_cookie_trocado_401(self, client, fazer_login, admin):
        import jwt as pyjwt

        from app.config import get_settings

        fazer_login(ADMIN["email"], ADMIN["senha"])
        # Forja um token com outro subject (outro usuario que nem existe)
        s = get_settings()
        payload = {
            "sub": "9999",
            "perfil": "ADMIN",
            "csrf": "x",
            "exp": 9_999_999_999,
        }
        client.cookies.set(
            s.auth_cookie_name,
            pyjwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm),
        )
        assert client.get("/api/auth/me").status_code == 401

    def test_me_com_usuario_desativado_401(self, client, fazer_login, admin, db_session):
        fazer_login(ADMIN["email"], ADMIN["senha"])
        admin.ativo = False
        db_session.commit()
        assert client.get("/api/auth/me").status_code == 401


# --------------------------------------------------------------- CSRF

class TestCSRF:
    def test_mutante_sem_cookie_401(self, client):
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 401
        assert "sessao" in resp.json()["detail"].lower()

    def test_mutante_com_cookie_sem_header_403(self, client, csrf_admin):
        resp = client.post("/api/auth/logout")  # cookie esta no client
        assert resp.status_code == 403
        assert "csrf" in resp.json()["detail"].lower()

    def test_mutante_com_csrf_errado_403(self, client, csrf_admin):
        resp = client.post(
            "/api/auth/logout", headers={CSRF_HEADER: "token-de-atacante"}
        )
        assert resp.status_code == 403

    def test_get_nao_exige_csrf(self, client, csrf_admin):
        assert client.get("/api/auth/me").status_code == 200


# ------------------------------------------------------- rate limiting

class TestRateLimit:
    def test_bloqueia_apos_5_tentativas_mesmo_email(self, client, admin, app):
        from app.config import get_settings

        app.state.limiter.reset()
        for _ in range(get_settings().rate_limit_login_email):
            client.post(
                "/api/auth/login",
                json={"email": ADMIN["email"], "senha": "Errada@1"},
            )
        resp = client.post(
            "/api/auth/login", json={"email": ADMIN["email"], "senha": "Errada@1"}
        )
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers

    def test_bloqueia_apos_20_requisicoes_mesmo_ip(self, client, admin, app):
        from app.config import get_settings

        app.state.limiter.reset()
        limite_ip = get_settings().rate_limit_login_ip
        for i in range(limite_ip):
            # emails diferentes: nao estoura o limite por email
            client.post(
                "/api/auth/login",
                json={"email": f"falso{i}@x.adv", "senha": "Senha@123"},
            )
        resp = client.post(
            "/api/auth/login", json={"email": "qualquer@x.adv", "senha": "Senha@123"}
        )
        assert resp.status_code == 429

    def test_login_valido_continua_funcionando_para_outro_email(
        self, client, admin, advogada, app
    ):
        from app.config import get_settings

        app.state.limiter.reset()
        for _ in range(get_settings().rate_limit_login_email):
            client.post(
                "/api/auth/login",
                json={"email": ADMIN["email"], "senha": "Errada@1"},
            )
        # outro email no mesmo IP ainda nao atingiu o limite de email
        resp = client.post(
            "/api/auth/login", json={"email": PADRAO["email"], "senha": PADRAO["senha"]}
        )
        assert resp.status_code == 200


# --------------------------------------------------------------- logout

class TestLogout:
    def test_logout_ok_apaga_cookie_e_sessao_morre(self, client, csrf_admin):
        resp = client.post("/api/auth/logout", headers={CSRF_HEADER: csrf_admin})
        assert resp.status_code == 204
        # cookie removido no client (TestClient respeita Max-Age=0)
        assert client.get("/api/auth/me").status_code == 401


# ---------------------------------------------------- autorizacao (RF02)

class TestAutorizacao:
    def test_listar_sem_sessao_401(self, client):
        assert client.get("/api/usuarios").status_code == 401

    def test_listar_como_padrao_403(self, client, fazer_login, advogada):
        fazer_login(PADRAO["email"], PADRAO["senha"])
        resp = client.get("/api/usuarios")
        assert resp.status_code == 403
        assert "admin" in resp.json()["detail"].lower()

    def test_listar_como_admin_ok(self, client, csrf_admin, admin, advogada):
        resp = client.get("/api/usuarios")
        assert resp.status_code == 200
        emails = {u["email"] for u in resp.json()}
        assert emails == {ADMIN["email"], PADRAO["email"]}

    def test_listar_nunca_vaza_senha_hash(self, client, csrf_admin, admin):
        resp = client.get("/api/usuarios")
        assert "senha_hash" not in resp.text

    def test_criar_como_admin_com_csrf_ok(self, client, csrf_admin):
        resp = client.post(
            "/api/usuarios",
            headers={CSRF_HEADER: csrf_admin},
            json={
                "nome": "Novo Advogado",
                "email": "novo@jadilson.adv",
                "senha": "Novo@1234",
                "perfil": "PADRAO",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["email"] == "novo@jadilson.adv"
        assert "senha_hash" not in resp.text

    def test_criar_como_padrao_403(self, client, csrf_admin, advogada):
        # login como admin p/ ter CSRF, depois loga como padrao (cookie troca)
        fazer_login_resp = client.post(
            "/api/auth/login", json={"email": PADRAO["email"], "senha": PADRAO["senha"]}
        )
        csrf_padrao = fazer_login_resp.json()["csrf_token"]
        resp = client.post(
            "/api/usuarios",
            headers={CSRF_HEADER: csrf_padrao},
            json={
                "nome": "X",
                "email": "x@jadilson.adv",
                "senha": "Senha@123",
                "perfil": "PADRAO",
            },
        )
        assert resp.status_code == 403

    def test_criar_email_duplicado_409(self, client, csrf_admin, admin):
        resp = client.post(
            "/api/usuarios",
            headers={CSRF_HEADER: csrf_admin},
            json={
                "nome": "Duplicado",
                "email": ADMIN["email"],
                "senha": "Senha@123",
                "perfil": "PADRAO",
            },
        )
        assert resp.status_code == 409


# ------------------------------------------------------------- headers

class TestHeadersSeguranca:
    def test_headers_de_seguranca_presentes(self, client):
        resp = client.get("/health")
        assert resp.headers["Cache-Control"] == "no-store"
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


# ------------------------------------------- tokens malformados devem dar 401

class TestTokenMalformado:
    def _set_cookie(self, client, payload):
        import jwt as pyjwt

        from app.config import get_settings

        s = get_settings()
        client.cookies.set(
            s.auth_cookie_name,
            pyjwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm),
        )

    def test_token_sem_sub_401_nao_500(self, client):
        self._set_cookie(client, {"exp": 9_999_999_999, "csrf": "x"})
        assert client.get("/api/auth/me").status_code == 401

    def test_token_sub_nao_numerico_401_nao_500(self, client):
        self._set_cookie(
            client, {"sub": "abc", "exp": 9_999_999_999, "csrf": "x"}
        )
        assert client.get("/api/auth/me").status_code == 401


# ------------------------------------------------- logout revoga o token

class TestRevogacaoAposLogout:
    def test_token_antigo_morre_apos_logout(self, client, csrf_admin, fazer_login, admin):
        import jwt as pyjwt

        from app.config import get_settings

        s = get_settings()
        token_antigo = client.cookies.get(s.auth_cookie_name)
        resp = client.post("/api/auth/logout", headers={CSRF_HEADER: csrf_admin})
        assert resp.status_code == 204
        # reenvia o token antigo (como um atacante que o roubou faria)
        client.cookies.set(s.auth_cookie_name, token_antigo)
        assert client.get("/api/auth/me").status_code == 401


# --------------------------------------------- validacoes de cadastro (422)

class TestValidacaoCadastro:
    def test_senha_muito_longa_422(self, client, csrf_admin):
        resp = client.post(
            "/api/usuarios",
            headers={CSRF_HEADER: csrf_admin},
            json={
                "nome": "X",
                "email": "longa@jadilson.adv",
                "senha": "A" * 100,  # > 72 bytes (limite bcrypt)
                "perfil": "PADRAO",
            },
        )
        assert resp.status_code == 422

    def test_nome_muito_longo_422(self, client, csrf_admin):
        resp = client.post(
            "/api/usuarios",
            headers={CSRF_HEADER: csrf_admin},
            json={
                "nome": "N" * 300,  # coluna String(120)
                "email": "nomelongo@jadilson.adv",
                "senha": "Senha@123",
                "perfil": "PADRAO",
            },
        )
        assert resp.status_code == 422


# ------------------------------------- CORS agora envolve os erros do CSRF

class TestCSRFCors:
    def test_erro_de_sessao_deve_ter_header_cors(self, client):
        """Antes o 401 do middleware CSRF saia sem CORS (bloqueava o front em prod)."""
        resp = client.post(
            "/api/auth/logout", headers={"Origin": "http://localhost:5173"}
        )
        assert resp.status_code == 401
        assert resp.headers["access-control-allow-origin"] == "http://localhost:5173"
