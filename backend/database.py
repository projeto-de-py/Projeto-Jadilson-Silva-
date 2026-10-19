from contextlib import contextmanager
import mysql.connector

PUBLIC='u.id, u.nome, u.email, u.perfil, u.ativo, u.criado_em, u.atualizado_em'
class Database:
    def __init__(self,config): self.config=config
    @contextmanager
    def connect(self):
        c=self.config
        conn=mysql.connector.connect(host=c.mysql_host,port=c.mysql_port,database=c.mysql_database,user=c.mysql_user,password=c.mysql_password,connection_timeout=5,time_zone='+00:00',autocommit=False)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally: conn.close()
    def one(self,query,args):
        with self.connect() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(query,args)
                return cur.fetchone()
    def execute(self,query,args):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query,args)
                return cur.rowcount
    def find_user(self,email):
        return self.one(f'SELECT {PUBLIC}, u.senha_hash FROM usuarios u WHERE u.email=%s',(email,))
    def session(self,digest):
        return self.one(f'''SELECT {PUBLIC}, s.csrf_token FROM sessoes s
        JOIN usuarios u ON u.id=s.usuario_id
        WHERE s.id_hash=%s AND s.revogada_em IS NULL AND s.expira_em>UTC_TIMESTAMP() AND u.ativo=1''',(digest,))
    def create_session(self,digest,user,csrf,expires):
        self.execute('INSERT INTO sessoes (id_hash,usuario_id,csrf_token,expira_em) VALUES (%s,%s,%s,%s)',(digest,user,csrf,expires))
    def revoke(self,digest):
        self.execute('UPDATE sessoes SET revogada_em=UTC_TIMESTAMP() WHERE id_hash=%s AND revogada_em IS NULL',(digest,))
