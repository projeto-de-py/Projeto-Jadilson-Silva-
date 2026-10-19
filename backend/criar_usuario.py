"""Cadastro administrativo local; nunca disponibilizado como endpoint publico."""
from getpass import getpass
from pydantic import BaseModel,EmailStr,SecretStr,Field,field_validator
from argon2 import PasswordHasher
from mysql.connector import Error
from config import Config
from database import Database
class Cadastro(BaseModel):
    nome: str=Field(min_length=1,max_length=120)
    email: EmailStr=Field(max_length=254)
    senha: SecretStr
    @field_validator('nome')
    @classmethod
    def nome_valido(cls,v):
        v=v.strip()
        if not v: raise ValueError('Nome obrigatorio')
        return v
    @field_validator('senha')
    @classmethod
    def senha_valida(cls,v):
        if not 8<=len(v.get_secret_value())<=1024 or not v.get_secret_value().strip(): raise ValueError('Senha deve ter entre 8 e 1024 caracteres')
        return v

def main():
    from pydantic import ValidationError
    name=input('Nome: '); email=input('E-mail: '); profile=input('Perfil (padrao/admin): ')
    if profile not in ('padrao','admin'): raise SystemExit('Perfil invalido.')
    password=getpass('Senha (oculta): ')
    if password!=getpass('Confirme a senha (oculta): '): raise SystemExit('Senhas diferentes.')
    try: data=Cadastro(nome=name,email=email,senha=password)
    except ValidationError: raise SystemExit('Dados invalidos; confira nome, e-mail e tamanho da senha.')
    try:
        Database(Config.load()).execute('INSERT INTO usuarios (nome,email,senha_hash,perfil) VALUES (%s,%s,%s,%s)',(data.nome,str(data.email).casefold(),PasswordHasher().hash(data.senha.get_secret_value()),profile))
    except Error as e:
        raise SystemExit('E-mail ja cadastrado.' if e.errno==1062 else 'Nao foi possivel cadastrar o usuario; confira a preparacao do banco.')
    print('Usuario cadastrado. Nenhuma senha foi exibida.')
if __name__=='__main__': main()
