"""Testes reais exclusivos de usuarios/sessoes. Não cria tabelas de domínio."""
import os
import sys
import secrets
import uuid
import json
from pathlib import Path
from datetime import datetime, timedelta
import pytest
import mysql.connector as mysql
from fastapi import Depends
from fastapi.testclient import TestClient
from config import Config
from database import Database
from main import create_app
from auth import COOKIE, digest, hasher, require_admin

pytestmark = pytest.mark.skipif(os.getenv('RUN_MYSQL_TESTS') != '1', reason='MySQL real não habilitado')
PREP = Path(__file__).resolve().parents[1]/'banco'

@pytest.fixture(scope='module')
def real(request):
    config = Config.load()
    store = Database(config)
    admin = mysql.connect(user='root', password=getattr(request.config, 'mysql_admin_password', ''), unix_socket=os.getenv('MYSQL_ADMIN_SOCKET','/tmp/mysql.sock'), database='sistema', time_zone='+00:00')
    cur = admin.cursor(dictionary=True)
    cur.execute('SELECT @@general_log AS general_log')
    assert not cur.fetchone()['general_log']
    cur.execute('SET SESSION sql_log_bin=0')
    marker = 'teste_auth_' + uuid.uuid4().hex
    password = secrets.token_urlsafe(24) + ' '
    users = []
    try:
        for profile, active in [('padrao', True), ('admin', True), ('padrao', False)]:
            email = f'{marker}_{len(users)}@example.com'
            cur.execute('INSERT INTO usuarios(nome,email,senha_hash,perfil,ativo) VALUES(%s,%s,%s,%s,%s)', (marker, email, hasher.hash(password), profile, active))
            users.append((cur.lastrowid, email))
        admin.commit()
        yield config, store, admin, cur, users, password, marker
    finally:
        admin.rollback()
        for uid, email in users:
            cur.execute('DELETE FROM sessoes WHERE usuario_id=%s', (uid,))
            cur.execute('DELETE FROM usuarios WHERE id=%s AND email=%s', (uid, email))
        admin.commit()
        for uid, email in users:
            cur.execute('SELECT COUNT(*) AS n FROM usuarios WHERE id=%s AND email=%s', (uid, email))
            assert cur.fetchone()['n'] == 0
            cur.execute('SELECT COUNT(*) AS n FROM sessoes WHERE usuario_id=%s', (uid,))
            assert cur.fetchone()['n'] == 0
        cur.close()
        admin.close()

def test_connection_structure_permissions(real):
    config, store, _, cur, _, _, _ = real
    sys.path.insert(0, str(PREP))
    from preparar_autenticacao import divergences, PERMS
    expected = json.loads((PREP/'estrutura_esperada.json').read_text())
    assert set(PERMS) == {'usuarios', 'sessoes'}
    for table in PERMS:
        assert not divergences(cur, table, expected[table])
    with store.connect() as conn:
        with conn.cursor(dictionary=True) as appcur:
            appcur.execute('SELECT CURRENT_USER() AS usuario, DATABASE() AS banco')
            assert appcur.fetchone() == {'usuario': 'sistema_app@localhost', 'banco': 'sistema'}
            appcur.execute('SHOW GRANTS')
            grants = [next(iter(row.values())) for row in appcur.fetchall()]
            assert all('WITH GRANT OPTION' not in grant for grant in grants)
            import re
            actual = {}
            for grant in grants:
                if grant.startswith('GRANT USAGE ON *.*'):
                    continue
                match = re.match(r'GRANT (.+) ON `sistema`\.`([^`]+)` TO ', grant)
                assert match is not None
                actual[match[2]] = set(match[1].split(', '))
            assert actual == PERMS
            for statement, code in [('DELETE FROM usuarios WHERE FALSE', 1142), ('DELETE FROM sessoes WHERE FALSE', 1142), ('CREATE TEMPORARY TABLE teste_auth_permissoes(id INT)', 1044)]:
                with pytest.raises(mysql.Error) as exc:
                    appcur.execute(statement)
                assert exc.value.errno == code

def test_defaults_duplicate_email_argon2(real):
    _, store, admin, cur, users, password, marker = real
    email = marker + '_defaults@example.com'
    hashed = hasher.hash(password)
    with store.connect() as conn:
        with conn.cursor(dictionary=True) as appcur:
            appcur.execute('INSERT INTO usuarios(nome,email,senha_hash) VALUES(%s,%s,%s)', (marker, email, hashed))
            uid = appcur.lastrowid
            users.append((uid, email))
    with store.connect() as conn:
        with conn.cursor(dictionary=True) as appcur:
            appcur.execute('SELECT perfil,ativo,senha_hash,criado_em,atualizado_em FROM usuarios WHERE id=%s', (uid,))
            row = appcur.fetchone()
            assert row['perfil'] == 'padrao' and row['ativo'] == 1
            assert row['criado_em'] is not None and row['atualizado_em'] is not None
            assert row['senha_hash'].startswith('$argon2id$')
            assert hasher.verify(row['senha_hash'], password)
            with pytest.raises(mysql.Error) as exc:
                appcur.execute('INSERT INTO usuarios(nome,email,senha_hash) VALUES(%s,%s,%s)', (marker, email, hashed))
            assert exc.value.errno == 1062
            appcur.execute('UPDATE usuarios SET nome=%s WHERE id=%s', (marker + '_atualizado', uid))
            assert appcur.rowcount == 1
    # Refresh the administrative snapshot after the application commits.
    admin.commit()
    cur.execute('SELECT nome FROM usuarios WHERE id=%s', (uid,))
    assert cur.fetchone()['nome'] == marker + '_atualizado'
    admin.commit()

def test_login_registered_active_only(real):
    config, store, _, _, users, password, marker = real
    headers = {'origin': config.origin}
    app = create_app(config, store)
    @app.get('/api/test-admin')
    def admin_route(user=Depends(require_admin)):
        return {'ok': True}
    with TestClient(app) as client:
        assert client.get('/api/auth/session').status_code == 401
        assert client.post('/api/auth/login', json={'email': 'invalido', 'senha': 'segredo'}, headers=headers).status_code == 422
        rejected = []
        for email, pw in [(users[0][1], 'incorreta'), (marker + '_ausente@example.com', password), (users[2][1], password)]:
            response = client.post('/api/auth/login', json={'email': email, 'senha': pw}, headers=headers)
            assert response.status_code == 401
            rejected.append(response.json())
        assert rejected[0] == rejected[1] == rejected[2]
        response = client.post('/api/auth/login', json={'email': users[0][1].upper(), 'senha': password}, headers=headers)
        assert response.status_code == 200
        assert set(response.json()['usuario']) == {'id','nome','email','perfil','ativo','criado_em','atualizado_em'}
        assert client.get('/api/test-admin').status_code == 403
        assert client.post('/api/auth/login', json={'email': users[1][1], 'senha': password.rstrip()}, headers=headers).status_code == 401
        assert client.post('/api/auth/login', json={'email': users[1][1], 'senha': password}, headers=headers).status_code == 200
        assert client.get('/api/test-admin').status_code == 200

def test_session_persistence_expiry_active_user(real):
    config, store, admin, cur, users, password, _ = real
    headers = {'origin': config.origin}
    uid, email = users[0]
    with TestClient(create_app(config, store)) as first:
        response = first.post('/api/auth/login', json={'email': email, 'senha': password}, headers=headers)
        assert response.status_code == 200
        cookie = response.headers['set-cookie']
        assert 'HttpOnly' in cookie and 'SameSite=strict' in cookie and 'Path=/api' in cookie
        token = first.cookies.get(COOKIE)
        # MySQL REPEATABLE READ must see the session committed by the API.
        admin.commit()
        cur.execute('SELECT id_hash FROM sessoes WHERE usuario_id=%s AND revogada_em IS NULL', (uid,))
        assert digest(token) in {row['id_hash'] for row in cur.fetchall()}
        with TestClient(create_app(config, store)) as restored:
            restored.cookies.update(first.cookies)
            assert restored.get('/api/auth/session').status_code == 200
            cur.execute('UPDATE usuarios SET ativo=0 WHERE id=%s', (uid,)); admin.commit()
            try:
                assert restored.get('/api/auth/session').status_code == 401
            finally:
                cur.execute('UPDATE usuarios SET ativo=1 WHERE id=%s', (uid,)); admin.commit()
            assert restored.get('/api/auth/session').status_code == 200
            cur.execute('UPDATE sessoes SET expira_em=UTC_TIMESTAMP()-INTERVAL 1 SECOND WHERE id_hash=%s', (digest(token),)); admin.commit()
            assert restored.get('/api/auth/session').status_code == 401

def test_logout_revocation_and_csrf(real):
    config, store, _, _, users, password, _ = real
    headers = {'origin': config.origin}
    with TestClient(create_app(config, store)) as client:
        response = client.post('/api/auth/login', json={'email': users[0][1], 'senha': password}, headers=headers)
        assert response.status_code == 200
        csrf = response.json()['csrf_token']
        with TestClient(create_app(config, store)) as replay:
            replay.cookies.update(client.cookies)
            assert client.post('/api/auth/logout', json={}, headers=headers).status_code == 403
            assert client.post('/api/auth/logout', json={}, headers={**headers, 'X-CSRF-Token': 'incorreto'}).status_code == 403
            assert client.post('/api/auth/logout', json={}, headers={'origin': 'https://example.invalid', 'X-CSRF-Token': csrf}).status_code == 403
            assert replay.get('/api/auth/session').status_code == 200
            assert client.post('/api/auth/logout', json={}, headers={**headers, 'X-CSRF-Token': csrf}).status_code == 204
            assert client.get('/api/auth/session').status_code == 401
            assert replay.get('/api/auth/session').status_code == 401

def test_session_rotation_attempt_limit(real):
    config, store, _, _, users, password, _ = real
    headers = {'origin': config.origin}
    credentials = {'email': users[1][1], 'senha': password}
    with TestClient(create_app(config, store)) as client:
        assert client.post('/api/auth/login', json=credentials, headers=headers).status_code == 200
        with TestClient(create_app(config, store)) as old:
            old.cookies.update(client.cookies)
            assert client.post('/api/auth/login', json=credentials, headers=headers).status_code == 200
            assert old.get('/api/auth/session').status_code == 401
            assert client.get('/api/auth/session').status_code == 200
    with TestClient(create_app(config, store)) as client:
        for _ in range(5):
            assert client.post('/api/auth/login', json={'email': users[0][1], 'senha': 'errada'}, headers=headers).status_code == 401
        assert client.post('/api/auth/login', json={'email': users[0][1], 'senha': password}, headers=headers).status_code == 429
