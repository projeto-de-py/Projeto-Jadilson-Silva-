"""Persistencia MySQL: uma conexao e uma transacao por unidade de trabalho.

Nao reutiliza conexoes interrompidas nem repete escritas automaticamente:
se a resposta de COMMIT se perder, o resultado pode ser indeterminado.
"""
from contextlib import contextmanager
import logging

import mysql.connector

logger = logging.getLogger(__name__)
PUBLIC = "u.id, u.nome, u.email, u.perfil, u.ativo, u.criado_em, u.atualizado_em"
FIND_USER = f"SELECT {PUBLIC}, u.senha_hash FROM usuarios u WHERE u.email=%s"
FIND_SESSION = f"""SELECT {PUBLIC}, s.csrf_token FROM sessoes s
JOIN usuarios u ON u.id=s.usuario_id
WHERE s.id_hash=%s AND s.revogada_em IS NULL
AND s.expira_em>UTC_TIMESTAMP() AND u.ativo=1"""
INSERT_SESSION = """INSERT INTO sessoes
(id_hash,usuario_id,csrf_token,expira_em) VALUES (%s,%s,%s,%s)"""
REVOKE_SESSION = """UPDATE sessoes SET revogada_em=UTC_TIMESTAMP()
WHERE id_hash=%s AND revogada_em IS NULL"""


def _cleanup(conn, operation):
    """Falhas de limpeza nao podem ocultar a causa nem um COMMIT confirmado."""
    try:
        getattr(conn, operation)()
    except Exception:
        # Nunca logar excecao/SQL/parametros: podem conter credenciais ou tokens.
        logger.warning("Falha na limpeza da conexao MySQL (%s).", operation)


class Database:
    def __init__(self, config):
        self.config = config

    def _connection_options(self):
        c = self.config
        options = dict(
            host=c.mysql_host, port=c.mysql_port, database=c.mysql_database,
            user=c.mysql_user, password=c.mysql_password,
            connection_timeout=c.mysql_connect_timeout,
            read_timeout=c.mysql_read_timeout, write_timeout=c.mysql_write_timeout,
            charset="utf8mb4", collation="utf8mb4_unicode_ci",
            time_zone="+00:00", autocommit=False,
        )
        if c.mysql_ssl_ca:
            options.update(ssl_ca=c.mysql_ssl_ca, ssl_verify_cert=True,
                           ssl_verify_identity=True, ssl_disabled=False)
        return options

    @contextmanager
    def connect(self, *, read_only=False):
        """Commit unico; rollback em falha; fechamento mesmo apos desconexao.

        read_only ativa protecao do servidor para consultas de leitura.
        Uma nova chamada sempre abre uma conexao independente e atualizada.
        """
        conn = mysql.connector.connect(**self._connection_options())
        try:
            if read_only:
                conn.start_transaction(readonly=True)
            yield conn
            conn.commit()
        except BaseException:
            _cleanup(conn, "rollback")
            raise
        finally:
            _cleanup(conn, "close")

    def one(self, query, args):
        with self.connect(read_only=True) as conn:
            # Buffered consome o resultado antes do fechamento/COMMIT.
            with conn.cursor(dictionary=True, buffered=True) as cur:
                cur.execute(query, args)
                return cur.fetchone()

    def execute(self, query, args):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, args)
                return cur.rowcount

    def find_user(self, email):
        return self.one(FIND_USER, (email,))

    def session(self, digest):
        return self.one(FIND_SESSION, (digest,))

    def create_session(self, digest, user, csrf, expires, *, previous_digest=None):
        """Substitui a sessao apresentada e cria a nova no mesmo COMMIT.

        Falha no INSERT preserva a sessao anterior pelo rollback. O UPDATE
        pela PK serializa revogacoes concorrentes dessa sessao no InnoDB.
        Logins independentes continuam podendo criar sessoes independentes.
        """
        with self.connect() as conn:
            with conn.cursor() as cur:
                if previous_digest is not None:
                    cur.execute(REVOKE_SESSION, (previous_digest,))
                cur.execute(INSERT_SESSION, (digest, user, csrf, expires))

    def revoke(self, digest):
        # Idempotente: nao altera novamente uma sessao ja revogada.
        self.execute(REVOKE_SESSION, (digest,))
