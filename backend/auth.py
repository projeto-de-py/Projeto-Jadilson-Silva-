import hashlib,secrets,time
from collections import deque
from threading import Lock
from fastapi import HTTPException,Request
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError,InvalidHashError

hasher=PasswordHasher()
DUMMY=hasher.hash(secrets.token_urlsafe(32))
COOKIE='jadilson_session'
def digest(token): return hashlib.sha256(token.encode()).hexdigest()
def verify(password,stored):
    try: return hasher.verify(stored,password)
    except (VerificationError,InvalidHashError): return False
class Limiter:
    """Janela deslizante, limitada em memoria. Executar um unico worker."""
    def __init__(self): self.buckets={}; self.lock=Lock()
    def check(self,key,limit,window=300):
        now=time.monotonic()
        with self.lock:
            # Evita crescimento ilimitado e nao expulsa buckets ativos.
            if len(self.buckets)>=10000:
                self.buckets={k:v for k,v in self.buckets.items() if v and v[-1]>now-window}
                if len(self.buckets)>=10000 and key not in self.buckets: raise HTTPException(429,'Muitas tentativas. Aguarde e tente novamente.',headers={'Retry-After':str(window)})
            bucket=self.buckets.setdefault(key,deque())
            while bucket and bucket[0]<=now-window: bucket.popleft()
            if len(bucket)>=limit: raise HTTPException(429,'Muitas tentativas. Aguarde e tente novamente.',headers={'Retry-After':str(window)})
            bucket.append(now)
def current_user(request: Request):
    token=request.cookies.get(COOKIE,'')
    if not 40<=len(token)<=128: raise HTTPException(401,'Sessao expirada. Entre novamente.')
    row=request.app.state.db.session(digest(token))
    if not row: raise HTTPException(401,'Sessao expirada. Entre novamente.')
    request.state.session_hash=digest(token)
    request.state.csrf=row.pop('csrf_token')
    return row
def require_csrf(request: Request):
    row=current_user(request)
    supplied=request.headers.get('X-CSRF-Token','')
    if not secrets.compare_digest(supplied.encode('utf-8'),request.state.csrf.encode('utf-8')): raise HTTPException(403,'Requisicao nao autorizada.')
    return row
def require_admin(request: Request):
    user=require_csrf(request) if request.method not in ('GET','HEAD','OPTIONS') else current_user(request)
    if user['perfil']!='admin': raise HTTPException(403,'Acesso nao permitido.')
    return user
