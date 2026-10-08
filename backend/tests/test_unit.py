from datetime import datetime,timedelta
from dataclasses import replace
import secrets
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from pydantic import ValidationError,SecretStr
from config import Config
from main import create_app,LoginInput
from auth import digest,hasher,require_admin

CONFIG=Config('127.0.0.1',3306,'sistema','sistema_app','teste-unitario','http://127.0.0.1:5173',False,3600)
HEADERS={'origin':CONFIG.origin}
class MemoryDB:
    def __init__(self):
        now=datetime.now()
        self.users={email:{'id':n,'nome':'Pessoa de teste','email':email,'perfil':profile,'ativo':active,'criado_em':now,'atualizado_em':now,'senha_hash':hasher.hash('senha-unitaria-com-espacos ')} for n,(email,active,profile) in enumerate([('teste@example.com',True,'padrao'),('inativo@example.com',False,'padrao'),('admin@example.com',True,'admin')],1)}
        self.sessions={}
    def find_user(self,email): return self.users.get(email)
    def create_session(self,key,user,csrf,expires): self.sessions[key]={'user':user,'csrf':csrf,'expires':expires,'revoked':False}
    def revoke(self,key):
        if key in self.sessions: self.sessions[key]['revoked']=True
    def session(self,key):
        s=self.sessions.get(key)
        if not s or s['revoked'] or s['expires']<=datetime.now(): return None
        user=next(u for u in self.users.values() if u['id']==s['user'])
        return dict(user,csrf_token=s['csrf']) if user['ativo'] else None
@pytest.fixture
def setup():
    store=MemoryDB(); app=create_app(CONFIG,store)
    @app.get('/api/test-admin')
    def admin(user=Depends(require_admin)): return {'ok':True}
    return app,store,TestClient(app)
def login(client,email='teste@example.com',senha='senha-unitaria-com-espacos '):
    return client.post('/api/auth/login',json={'email':email,'senha':senha},headers=HEADERS)
def test_validation_hides_inputs(setup):
    _,_,client=setup
    response=login(client,email='email-invalido',senha='segredo-nao-retornar')
    assert response.status_code==422
    assert 'segredo-nao-retornar' not in response.text
    assert login(client,senha='').status_code==422
    assert LoginInput(email='teste@example.com',senha=' senha com espacos ').senha.get_secret_value()==' senha com espacos '
def test_authenticated_cycle(setup):
    app,store,client=setup
    assert client.get('/api/auth/session').status_code==401
    result=login(client); assert result.status_code==200
    data=result.json(); assert 'senha_hash' not in result.text and 'senha' not in data['usuario']
    cookie=result.headers['set-cookie']; assert 'HttpOnly' in cookie and 'SameSite=strict' in cookie and 'Path=/api' in cookie
    assert client.get('/api/auth/session').status_code==200
    assert client.get('/api/test-admin').status_code==403
    new_client=TestClient(app); new_client.cookies.update(client.cookies)
    assert new_client.get('/api/auth/session').status_code==200
    assert client.post('/api/auth/logout',json={},headers=HEADERS).status_code==403
    assert client.post('/api/auth/logout',json={},headers={**HEADERS,'X-CSRF-Token':data['csrf_token']}).status_code==204
    assert new_client.get('/api/auth/session').status_code==401
@pytest.mark.parametrize('email,senha',[('teste@example.com','errada'),('ausente@example.com','errada'),('inativo@example.com','senha-unitaria-com-espacos ')])
def test_generic_error(setup,email,senha):
    result=login(setup[2],email,senha)
    assert result.status_code==401 and result.json()=={'detail':'E-mail ou senha invalidos.'}
def test_origin_and_limit(setup):
    client=setup[2]
    assert client.post('/api/auth/login',json={'email':'teste@example.com','senha':'qualquer'},headers={'origin':'https://outro.example'}).status_code==403
    assert client.post('/api/auth/login',json={}).status_code==403
    for _ in range(5): assert login(client,senha='errada').status_code==401
    assert login(client,senha='errada').status_code==429
def test_expiration_and_inactivation(setup):
    _,store,client=setup
    assert login(client).status_code==200
    session=next(iter(store.sessions.values())); session['expires']=datetime.now()-timedelta(seconds=1)
    assert client.get('/api/auth/session').status_code==401
    assert login(client).status_code==200
    store.users['teste@example.com']['ativo']=False
    assert client.get('/api/auth/session').status_code==401
def test_rotation_and_production(setup):
    app,store,client=setup
    assert login(client).status_code==200
    old=TestClient(app); old.cookies.update(client.cookies)
    assert login(client).status_code==200
    assert old.get('/api/auth/session').status_code==401
    secure=create_app(replace(CONFIG,production=True,origin='https://portal.example.com'),store)
    secure_client=TestClient(secure,base_url='https://portal.example.com')
    result=secure_client.post('/api/auth/login',json={'email':'admin@example.com','senha':'senha-unitaria-com-espacos '},headers={'origin':'https://portal.example.com'})
    assert result.status_code==200 and 'Secure' in result.headers['set-cookie']
def test_admin_role_from_database(setup):
    app,store,client=setup
    assert login(client,'admin@example.com').status_code==200
    assert client.get('/api/test-admin').status_code==200
    store.users['admin@example.com']['perfil']='padrao'
    assert client.get('/api/test-admin').status_code==403

def test_ip_limit_for_invalid_inputs(setup):
    client=setup[2]
    for _ in range(20): assert login(client,email='invalido').status_code==422
    assert login(client,email='invalido').status_code==429

def test_wrong_csrf_and_oversized_input(setup):
    client=setup[2]
    assert login(client).status_code==200
    for value in ('incorreto','nao-ascii-é'):
        # HTTP headers devem ser latin1; TestClient exige bytes para valor nao ASCII.
        headers={**HEADERS,'X-CSRF-Token':value.encode('utf-8')} if value!='incorreto' else {**HEADERS,'X-CSRF-Token':value}
        assert client.post('/api/auth/logout',json={},headers=headers).status_code==403
    assert client.post('/api/auth/login',content='x'*5000,headers={**HEADERS,'content-type':'application/json'}).status_code==413
    assert client.post('/api/auth/login',json={'email':'teste@example.com','senha':'teste','perfil':'admin'},headers=HEADERS).status_code==422

def test_database_error_is_generic(setup):
    from mysql.connector import Error
    app,store,client=setup
    def unavailable(email): raise Error('detalhe-interno-nao-retornar',errno=2003)
    store.find_user=unavailable
    response=login(client)
    assert response.status_code==503
    assert 'detalhe-interno-nao-retornar' not in response.text
