"""Administracao local, lock exclusivo, comparacao antes de qualquer DDL.
Nenhuma alteracao de tabela existente e aplicada automaticamente.
"""
from pathlib import Path
from getpass import getpass
import json,os,secrets,fcntl,sys
import mysql.connector as db
from dotenv import dotenv_values

BASE=Path(__file__).resolve().parent
BACKEND=BASE.parent
STATE=BACKEND/'.local/mysql'
PERMS={'usuarios':{'SELECT','INSERT','UPDATE'},'sessoes':{'SELECT','INSERT','UPDATE'}}
def atomic_env(path,content):
    if path.exists() and path.is_symlink(): raise RuntimeError('Arquivo de ambiente e link simbolico; revisar.')
    temporary=path.with_name(path.name+'.novo')
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f: f.write(content)
    os.chmod(temporary,0o600); os.replace(temporary,path)
def norm(value):
    return str(value).lower().replace('()','') if value is not None else None
def inspect(cur,table):
    cur.execute('SELECT ENGINE,TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s',('sistema',table))
    t=cur.fetchone()
    if t is None: return None
    cur.execute('SELECT COLUMN_NAME,COLUMN_TYPE,IS_NULLABLE,COLUMN_DEFAULT,EXTRA,COLLATION_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION',('sistema',table)); cols=cur.fetchall()
    cur.execute('SELECT INDEX_NAME,NON_UNIQUE,SEQ_IN_INDEX,COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY INDEX_NAME,SEQ_IN_INDEX',('sistema',table))
    indexes={}
    for row in cur.fetchall(): indexes.setdefault((row['INDEX_NAME'],row['NON_UNIQUE']),[]).append(row['COLUMN_NAME'])
    cur.execute('''SELECT k.COLUMN_NAME,k.REFERENCED_TABLE_SCHEMA,k.REFERENCED_TABLE_NAME,k.REFERENCED_COLUMN_NAME,r.DELETE_RULE,r.UPDATE_RULE
FROM information_schema.KEY_COLUMN_USAGE k JOIN information_schema.REFERENTIAL_CONSTRAINTS r
ON r.CONSTRAINT_SCHEMA=k.CONSTRAINT_SCHEMA AND r.CONSTRAINT_NAME=k.CONSTRAINT_NAME AND r.TABLE_NAME=k.TABLE_NAME
WHERE k.TABLE_SCHEMA=%s AND k.TABLE_NAME=%s''',('sistema',table))
    return t,cols,indexes,cur.fetchall()
def divergences(cur,table,spec):
    actual=inspect(cur,table)
    if actual is None: return []
    t,cols,idx,fks=actual; issues=[]
    if t!={'ENGINE':'InnoDB','TABLE_COLLATION':'utf8mb4_unicode_ci'}: issues.append('Engine/collation divergente')
    if [c['COLUMN_NAME'] for c in cols]!=list(spec['columns']): issues.append('Lista ou ordem de colunas divergente')
    for c in cols:
        expected=spec['columns'].get(c['COLUMN_NAME'])
        if expected is None: continue
        typ,nullable,default,extra=expected
        gotextra=norm(c['EXTRA']).replace('default_generated','').strip()
        expected_collation='ascii_bin' if table=='sessoes' and c['COLUMN_NAME'] in ('id_hash','csrf_token') else 'utf8mb4_unicode_ci'
        if (norm(c['COLUMN_TYPE']),c['IS_NULLABLE']=='YES',norm(c['COLUMN_DEFAULT']),gotextra)!=(norm(typ),nullable,norm(default),norm(extra).strip()): issues.append('Coluna divergente: '+c['COLUMN_NAME'])
        if c['COLLATION_NAME'] and c['COLLATION_NAME']!=expected_collation: issues.append('Collation da coluna: '+c['COLUMN_NAME'])
    if idx.get(('PRIMARY',0))!=spec['pk']: issues.append('PK divergente')
    unique=[v for (name,non),v in idx.items() if name!='PRIMARY' and non==0]
    if sorted(unique)!=sorted(spec['unique']): issues.append('Unicidade divergente')
    for needed in spec['indexes']:
        if not any(v[:len(needed)]==needed for v in idx.values()): issues.append('Indice ausente: '+','.join(needed))
    actual_fk={(r['COLUMN_NAME'],r['REFERENCED_TABLE_NAME'],r['REFERENCED_COLUMN_NAME']) for r in fks}
    if actual_fk!={tuple(x) for x in spec['fks']}: issues.append('FKs divergentes')
    if any(r['REFERENCED_TABLE_SCHEMA']!='sistema' or r['DELETE_RULE'] not in ('RESTRICT','NO ACTION') or r['UPDATE_RULE'] not in ('RESTRICT','NO ACTION') for r in fks): issues.append('Regra FK divergente')
    return issues

def main(admin_password=None):
    os.umask(0o077)
    STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (STATE/'preparacao.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with db.connect(user='root',password=getpass('Senha administrativa (oculta; Enter se vazia): ') if admin_password is None else admin_password,unix_socket=os.getenv('MYSQL_ADMIN_SOCKET','/tmp/mysql.sock'),time_zone='+00:00') as conn:
            cur=conn.cursor(dictionary=True)
            cur.execute('SELECT VERSION() AS versao,@@bind_address AS bind_address,@@port AS porta,@@general_log AS general_log'); server=cur.fetchone()
            if server['bind_address'] not in ('127.0.0.1','::1','127.0.0.1,::1') or server['general_log']: raise RuntimeError('Revisar loopback/general_log antes da preparacao.')
            cur.execute("SHOW VARIABLES LIKE 'mysqlx_bind_address'"); x=cur.fetchone()
            if x and x['Value'] not in ('127.0.0.1','::1','127.0.0.1,::1'): raise RuntimeError('MySQL X nao esta em loopback.')
            cur.execute('SET SESSION sql_log_bin=0')
            cur.execute("SELECT DEFAULT_CHARACTER_SET_NAME AS charset,DEFAULT_COLLATION_NAME AS collation FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='sistema'"); schema=cur.fetchone()
            if schema and schema!={'charset':'utf8mb4','collation':'utf8mb4_unicode_ci'}: raise RuntimeError('Charset/collation do banco existente divergente; preservado.')
            expected={k:v for k,v in json.loads((BASE/'estrutura_esperada.json').read_text()).items() if k in PERMS}
            issues={table:errors for table,spec in expected.items() if (errors:=divergences(cur,table,spec))}
            if issues:
                (STATE/'divergencias.json').write_text(json.dumps(issues,indent=2,ensure_ascii=False)+'\n')
                # DDL de destino acompanhado de bloqueio; nunca executar uma conversao cega.
                review='-- NAO EXECUTAR: plano de revisao, nao migracao automatica.\n-- Preservar dados; levantar SHOW CREATE TABLE e contagens; backup antes de conversoes.\n'
                for table,errors in issues.items(): review+='-- '+table+': '+'; '.join(errors)+'\n'
                review+='-- Destino documentado em estrutura_autenticacao.sql.\n-- Alteracoes de tipo/NULL/unicidade exigem avaliacao dos registros reais.\n'
                (STATE/'migracao_para_revisao.sql').write_text(review)
                raise RuntimeError('Estrutura existente divergente; revisar divergencias.json e migracao_para_revisao.sql.')
            cur.execute("SELECT User,Host FROM mysql.user WHERE User='sistema_app'"); accounts=cur.fetchall()
            env={**dotenv_values(BACKEND/'.env'),**dotenv_values(STATE/'.env')}
            if accounts:
                if accounts!=[{'User':'sistema_app','Host':'localhost'}]: raise RuntimeError('Contas sistema_app adicionais: preservar e revisar.')
                password=env.get('MYSQL_PASSWORD') or getpass('Senha atual sistema_app (oculta): ')
                with db.connect(user='sistema_app',password=password,host='127.0.0.1',port=server['porta']) as probe:
                    pc=probe.cursor(); pc.execute('SELECT CURRENT_USER()')
                    if pc.fetchone()[0]!='sistema_app@localhost': raise RuntimeError('Conta efetiva inesperada.')
                cur.execute("SHOW GRANTS FOR 'sistema_app'@'localhost'"); grants=[next(iter(r.values())) for r in cur.fetchall()]
                import re
                for grant in grants:
                    if grant.startswith('GRANT USAGE ON *.* TO'): continue
                    m=re.match(r'GRANT (.+) ON `sistema`\.`([^`]+)` TO ',grant)
                    if not m or 'WITH GRANT OPTION' in grant or m[2] not in PERMS or not set(m[1].split(', '))<=PERMS[m[2]]: raise RuntimeError('Acessos existentes fora do escopo: preservar e revisar.')
                cur.execute("SELECT COUNT(*) AS n FROM mysql.role_edges WHERE TO_USER='sistema_app'")
                if cur.fetchone()['n']: raise RuntimeError('Conta com roles existentes: preservar e revisar.')
            else: password=secrets.token_urlsafe(36)
            backend_env=dotenv_values(BACKEND/'.env') if (BACKEND/'.env').exists() else {}
            target_env={'MYSQL_HOST':'127.0.0.1','MYSQL_PORT':str(server['porta']),'MYSQL_DATABASE':'sistema','MYSQL_USER':'sistema_app','MYSQL_PASSWORD':password}
            if any(backend_env.get(k) not in (None,'',v) for k,v in target_env.items()): raise RuntimeError('Backend possui credenciais diferentes: preservar e revisar.')
            for file in ['estrutura_autenticacao.sql']:
                for stmt in '\n'.join(l for l in (BASE/file).read_text().splitlines() if not l.lstrip().startswith('--')).split(';'):
                    if stmt.strip(): cur.execute(stmt)
            envtext=f'MYSQL_HOST=127.0.0.1\nMYSQL_PORT={server["porta"]}\nMYSQL_DATABASE=sistema\nMYSQL_USER=sistema_app\nMYSQL_PASSWORD={password}\n'
            atomic_env(STATE/'.env',envtext)
            if not accounts: cur.execute("CREATE USER 'sistema_app'@'localhost' IDENTIFIED BY %s",(password,))
            for table,perms in PERMS.items(): cur.execute('GRANT '+', '.join(sorted(perms))+' ON sistema.`'+table+"` TO 'sistema_app'@'localhost'")
            conn.commit()
            backend_path=BACKEND/'.env'
            backend_lines=backend_path.read_text().splitlines() if backend_path.exists() else []
            for key,value in {**target_env,**{k:v for k,v in {'APP_ENV':'development','APP_ORIGIN':'http://127.0.0.1:5173','SESSION_SECONDS':'3600'}.items() if not backend_env.get(k)}}.items():
                prefix=key+'='
                backend_lines=[line for line in backend_lines if not line.strip().startswith(prefix)]
                backend_lines.append(prefix+value)
            atomic_env(backend_path,'\n'.join(backend_lines)+'\n')
            after={t:errors for t,s in expected.items() if (errors:=divergences(cur,t,s))}
            if after: raise RuntimeError('Estrutura apos criacao nao corresponde ao destino.')
            cur.execute("SHOW GRANTS FOR 'sistema_app'@'localhost'"); grants=[next(iter(r.values())) for r in cur.fetchall()]
            report={'status':'estrutura_e_acesso_verificados','servidor':server,'tabelas':list(expected),'permissoes':grants,'testes_funcionais':'nao_executados'}
            (STATE/'resultado_estrutura.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
            print('Estrutura e acesso verificados. Executar testes reais antes de declarar conclusao.')
if __name__=='__main__':
    try: main()
    except db.Error as e: print('Erro MySQL:',e.errno,'(detalhes omitidos).'); sys.exit(1)
