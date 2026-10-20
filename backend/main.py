from datetime import datetime,timedelta,timezone
import secrets
from fastapi import FastAPI,Request,Response,Depends,HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from mysql.connector import Error as MySQLError
from pydantic import BaseModel,EmailStr,SecretStr,Field,field_validator
from config import Config
from database import Database
from auth import COOKIE,DUMMY,Limiter,current_user,require_csrf,digest,verify

class LoginInput(BaseModel):
    model_config={'extra':'forbid'}
    email: EmailStr=Field(max_length=254)
    senha: SecretStr
    @field_validator('senha')
    @classmethod
    def check_password(cls,value):
        if not 1<=len(value.get_secret_value())<=1024: raise ValueError('Senha invalida')
        return value
class UsuarioPublico(BaseModel):
    id: int
    nome: str
    email: EmailStr
    perfil: str
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime
class SessionPublic(BaseModel):
    usuario: UsuarioPublico
    csrf_token: str

def create_app(config=None,db=None):
    config=config or Config.load()
    app=FastAPI(title='Autenticacao Jadilson',docs_url=None if config.production else '/docs',redoc_url=None)
    app.state.db=db or Database(config)
    app.state.limiter=Limiter()
    @app.exception_handler(RequestValidationError)
    async def validation_error(request,exc):
        # Nunca retorna o input recebido: pode conter senha.
        return JSONResponse({'detail':'Confira o e-mail e a senha informados.'},status_code=422)
    @app.exception_handler(MySQLError)
    async def database_error(request,exc):
        return JSONResponse({'detail':'Servico temporariamente indisponivel. Tente novamente.'},status_code=503)
    @app.middleware('http')
    async def protections(request,call_next):
        if request.method not in ('GET','HEAD','OPTIONS'):
            if request.headers.get('origin')!=config.origin:
                return JSONResponse({'detail':'Requisicao nao autorizada.'},status_code=403)
            if request.headers.get('content-type','').split(';')[0]!='application/json':
                return JSONResponse({'detail':'Envie os dados no formato JSON.'},status_code=415)
        if request.url.path=='/api/auth/login' and request.method=='POST':
            try: app.state.limiter.check('ip:'+(request.client.host if request.client else 'unknown'),20)
            except HTTPException as e: return JSONResponse({'detail':e.detail},status_code=e.status_code,headers=e.headers)
            try:
                if int(request.headers.get('content-length','0'))>4096:
                    return JSONResponse({'detail':'Dados de entrada muito grandes.'},status_code=413)
            except ValueError:
                return JSONResponse({'detail':'Requisicao invalida.'},status_code=400)
            body=await request.body()
            if len(body)>4096: return JSONResponse({'detail':'Dados de entrada muito grandes.'},status_code=413)
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        return response
    @app.post('/api/auth/login',response_model=SessionPublic)
    def login(data:LoginInput,request:Request,response:Response):
        email=str(data.email).casefold()
        app.state.limiter.check('email:'+digest(email),5)
        row=app.state.db.find_user(email)
        valid=verify(data.senha.get_secret_value(),row['senha_hash'] if row else DUMMY)
        if not row or not valid or not row['ativo']: raise HTTPException(401,'E-mail ou senha invalidos.')
        token=secrets.token_urlsafe(32); csrf=secrets.token_hex(32)
        old=request.cookies.get(COOKIE)
        previous_digest=digest(old) if old and 40<=len(old)<=128 else None
        expires=datetime.now(timezone.utc).replace(tzinfo=None)+timedelta(seconds=config.session_seconds)
        app.state.db.create_session(digest(token),row['id'],csrf,expires,previous_digest=previous_digest)
        response.set_cookie(COOKIE,token,max_age=config.session_seconds,httponly=True,secure=config.production,samesite='strict',path='/api')
        return {'usuario':row,'csrf_token':csrf}
    @app.get('/api/auth/session',response_model=SessionPublic)
    def session(request:Request,user=Depends(current_user)):
        return {'usuario':user,'csrf_token':request.state.csrf}
    @app.post('/api/auth/logout',status_code=204)
    def logout(request:Request,user=Depends(require_csrf)):
        app.state.db.revoke(request.state.session_hash)
        response=Response(status_code=204)
        response.delete_cookie(COOKIE,path='/api',httponly=True,secure=config.production,samesite='strict')
        return response
    return app

# uvicorn main:create_app --factory: importacao nao exige segredo em testes unitarios.
