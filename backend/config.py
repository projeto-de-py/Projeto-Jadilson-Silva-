import os
from dataclasses import dataclass,field
from pathlib import Path
from urllib.parse import urlsplit
from dotenv import load_dotenv

@dataclass(frozen=True)
class Config:
    mysql_host: str
    mysql_port: int
    mysql_database: str
    mysql_user: str
    mysql_password: str=field(repr=False)
    origin: str
    production: bool
    session_seconds: int
    @classmethod
    def load(cls):
        load_dotenv(Path(__file__).parent/'.env',override=False)
        production=os.getenv('APP_ENV','development')=='production'
        origin=os.getenv('APP_ORIGIN','http://127.0.0.1:5173').rstrip('/')
        parsed=urlsplit(origin)
        if parsed.scheme not in ('http','https') or not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
            raise RuntimeError('APP_ORIGIN invalida')
        if production and parsed.scheme!='https': raise RuntimeError('Producao exige HTTPS')
        if not production and parsed.hostname not in ('127.0.0.1','localhost','::1'):
            raise RuntimeError('Desenvolvimento exige origem local')
        password=os.getenv('MYSQL_PASSWORD','')
        if not password: raise RuntimeError('Configure MYSQL_PASSWORD no .env protegido do backend')
        user=os.getenv('MYSQL_USER','sistema_app')
        if user!='sistema_app': raise RuntimeError('Backend exige a conta restrita sistema_app')
        seconds=int(os.getenv('SESSION_SECONDS','3600'))
        if not 60<=seconds<=86400: raise RuntimeError('SESSION_SECONDS fora dos limites')
        return cls(os.getenv('MYSQL_HOST','127.0.0.1'),int(os.getenv('MYSQL_PORT','3306')),os.getenv('MYSQL_DATABASE','sistema'),user,password,origin,production,seconds)
