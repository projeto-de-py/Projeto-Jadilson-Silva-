"""Testes isolados: nenhum socket, .env ou banco real e acessado."""
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import mysql.connector
from fastapi.testclient import TestClient

from config import Config
from database import Database, FIND_USER, FIND_SESSION, INSERT_SESSION, REVOKE_SESSION
from banco.retencao_sessoes import COUNT_EXPIRED, planejar_limpeza
from main import create_app


def config():
    return Config("127.0.0.1", 3306, "isolado", "sistema_app", "somente-mock",
                  "http://127.0.0.1:5173", False, 3600)


def connection():
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    cur.rowcount = 1
    return conn, cur


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.db = Database(config())
        self.conn, self.cur = connection()
        self.patch = patch("database.mysql.connector.connect", return_value=self.conn)
        self.connect = self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_options_and_password_not_in_config_repr(self):
        self.db.find_user("synthetic@example.com")
        options = self.connect.call_args.kwargs
        self.assertEqual(options["connection_timeout"], 5)
        self.assertEqual(options["read_timeout"], 10)
        self.assertEqual(options["write_timeout"], 10)
        self.assertEqual(options["time_zone"], "+00:00")
        self.assertEqual(options["charset"], "utf8mb4")
        self.assertFalse(options["autocommit"])
        self.assertNotIn("somente-mock", repr(config()))

    def test_tls_ca_requires_certificate_and_identity(self):
        self.db = Database(replace(config(), mysql_ssl_ca="/mock/ca.pem"))
        with self.db.connect():
            pass
        options = self.connect.call_args.kwargs
        self.assertTrue(options["ssl_verify_cert"])
        self.assertTrue(options["ssl_verify_identity"])
        self.assertFalse(options["ssl_disabled"])

    def test_find_user_injection_is_parameter_not_sql(self):
        value = "' OR 1=1 --"
        self.cur.fetchone.return_value = None
        self.assertIsNone(self.db.find_user(value))
        self.cur.execute.assert_called_once_with(FIND_USER, (value,))
        self.assertNotIn(value, FIND_USER)
        self.conn.start_transaction.assert_called_once_with(readonly=True)
        self.conn.cursor.assert_called_once_with(dictionary=True, buffered=True)
        self.conn.commit.assert_called_once()
        self.conn.close.assert_called_once()

    def test_session_checks_expiry_revocation_active_and_parameter(self):
        self.db.session("synthetic-digest")
        self.cur.execute.assert_called_once_with(FIND_SESSION, ("synthetic-digest",))
        for clause in ("s.expira_em>UTC_TIMESTAMP()", "s.revogada_em IS NULL", "u.ativo=1", "u.id=s.usuario_id"):
            self.assertIn(clause, FIND_SESSION)

    def test_execute_preserves_user_persistence_interface(self):
        sql = "INSERT INTO usuarios (nome,email,senha_hash,perfil) VALUES (%s,%s,%s,%s)"
        args = ("Synthetic", "synthetic@example.com", "synthetic-hash", "padrao")
        self.assertEqual(self.db.execute(sql, args), 1)
        self.cur.execute.assert_called_once_with(sql, args)
        self.conn.commit.assert_called_once()
        self.conn.start_transaction.assert_not_called()

    def test_cursor_closed_before_commit(self):
        self.db.find_user("synthetic@example.com")
        events = [call[0] for call in self.conn.mock_calls]
        self.assertLess(events.index("cursor().__exit__"), events.index("commit"))
        self.assertLess(events.index("commit"), events.index("close"))

    def test_query_failure_rolls_back_and_closes(self):
        error = mysql.connector.OperationalError("synthetic", errno=2013)
        self.cur.execute.side_effect = error
        with self.assertRaises(mysql.connector.OperationalError) as caught:
            self.db.find_user("synthetic@example.com")
        self.assertIs(caught.exception, error)
        self.conn.commit.assert_not_called()
        self.conn.rollback.assert_called_once()
        self.conn.close.assert_called_once()

    def test_rollback_and_close_errors_do_not_hide_original(self):
        error = mysql.connector.OperationalError("synthetic-sensitive", errno=2013)
        self.cur.execute.side_effect = error
        self.conn.rollback.side_effect = RuntimeError("synthetic-sensitive")
        self.conn.close.side_effect = RuntimeError("synthetic-sensitive")
        with self.assertLogs("database", level="WARNING") as logs:
            with self.assertRaises(mysql.connector.OperationalError) as caught:
                self.db.find_user("synthetic@example.com")
        self.assertIs(caught.exception, error)
        self.assertNotIn("synthetic-sensitive", " ".join(logs.output))

    def test_commit_failure_not_retried(self):
        self.conn.commit.side_effect = mysql.connector.OperationalError("lost acknowledgement", errno=2013)
        with self.assertRaises(mysql.connector.OperationalError):
            self.db.revoke("synthetic-digest")
        self.connect.assert_called_once()
        self.cur.execute.assert_called_once()
        self.conn.rollback.assert_called_once()
        self.conn.close.assert_called_once()

    def test_close_failure_after_commit_does_not_report_write_failure(self):
        self.conn.close.side_effect = mysql.connector.OperationalError("synthetic", errno=2013)
        with self.assertLogs("database", level="WARNING"):
            self.assertEqual(self.db.execute("UPDATE synthetic SET value=%s", (1,)), 1)
        self.conn.commit.assert_called_once()
        self.conn.rollback.assert_not_called()

    def test_failed_read_only_begin_closes(self):
        self.conn.start_transaction.side_effect = mysql.connector.OperationalError("synthetic")
        with self.assertRaises(mysql.connector.OperationalError):
            self.db.find_user("synthetic@example.com")
        self.cur.execute.assert_not_called()
        self.conn.rollback.assert_called_once()
        self.conn.close.assert_called_once()

    def test_connect_failure_does_not_replay(self):
        self.connect.side_effect = mysql.connector.InterfaceError("synthetic", errno=2003)
        with self.assertRaises(mysql.connector.InterfaceError):
            self.db.find_user("synthetic@example.com")
        self.connect.assert_called_once()

    def test_next_operation_opens_new_connection_after_disconnect(self):
        first, first_cur = connection()
        second, second_cur = connection()
        first_cur.execute.side_effect = mysql.connector.OperationalError("synthetic", errno=2013)
        second_cur.fetchone.return_value = {"id": 1}
        self.connect.side_effect = [first, second]
        with self.assertRaises(mysql.connector.OperationalError):
            self.db.find_user("synthetic@example.com")
        self.assertEqual(self.db.find_user("synthetic@example.com"), {"id": 1})
        self.assertEqual(self.connect.call_count, 2)
        first.close.assert_called_once()
        second.close.assert_called_once()

    def test_rotation_uses_one_connection_one_commit(self):
        expiry = datetime(2030, 1, 1)
        self.db.create_session("new", 1, "csrf", expiry, previous_digest="old")
        self.assertEqual(self.cur.execute.call_args_list[0].args, (REVOKE_SESSION, ("old",)))
        self.assertEqual(self.cur.execute.call_args_list[1].args, (INSERT_SESSION, ("new", 1, "csrf", expiry)))
        self.connect.assert_called_once()
        self.conn.commit.assert_called_once()

    def test_insert_fk_failure_rolls_back_previous_revocation(self):
        self.cur.execute.side_effect = [None, mysql.connector.IntegrityError("synthetic FK", errno=1452)]
        with self.assertRaises(mysql.connector.IntegrityError):
            self.db.create_session("new", 999, "csrf", datetime(2030, 1, 1), previous_digest="old")
        self.conn.commit.assert_not_called()
        self.conn.rollback.assert_called_once()
        self.conn.close.assert_called_once()

    def test_duplicate_session_does_not_retry(self):
        self.cur.execute.side_effect = mysql.connector.IntegrityError("synthetic duplicate", errno=1062)
        with self.assertRaises(mysql.connector.IntegrityError):
            self.db.create_session("new", 1, "csrf", datetime(2030, 1, 1))
        self.connect.assert_called_once()
        self.conn.rollback.assert_called_once()

    def test_create_session_original_positional_interface(self):
        self.db.create_session("new", 1, "csrf", datetime(2030, 1, 1))
        self.cur.execute.assert_called_once_with(INSERT_SESSION, ("new", 1, "csrf", datetime(2030, 1, 1)))

    def test_revoke_is_conditional(self):
        self.db.revoke("old")
        self.cur.execute.assert_called_once_with(REVOKE_SESSION, ("old",))
        self.assertIn("revogada_em IS NULL", REVOKE_SESSION)

    def test_concurrent_calls_never_share_connection(self):
        created = []
        from threading import Lock
        lock = Lock()
        def factory(**kwargs):
            conn, cur = connection()
            cur.fetchone.return_value = {"id": 1}
            with lock:
                created.append(conn)
            return conn
        self.connect.side_effect = factory
        with ThreadPoolExecutor(max_workers=4) as executor:
            rows = list(executor.map(self.db.find_user, ["synthetic@example.com"] * 8))
        self.assertEqual(len(rows), 8)
        self.assertEqual(len(created), 8)
        for conn in created:
            conn.commit.assert_called_once()
            conn.close.assert_called_once()


class ConfigTests(unittest.TestCase):
    def load(self, **env):
        values = {"MYSQL_PASSWORD": "somente-mock", **env}
        with patch.dict(os.environ, values, clear=True), patch("config.load_dotenv"):
            return Config.load()

    def test_defaults_preserve_local_connection(self):
        value = self.load()
        self.assertEqual(value.mysql_database, "sistema")
        self.assertEqual(value.mysql_user, "sistema_app")
        self.assertEqual(value.mysql_connect_timeout, 5)

    def test_invalid_timeouts_rejected(self):
        for key in ("MYSQL_CONNECT_TIMEOUT", "MYSQL_READ_TIMEOUT", "MYSQL_WRITE_TIMEOUT"):
            for value in ("0", "121", "invalid"):
                with self.subTest(key=key, value=value), self.assertRaises(RuntimeError):
                    self.load(**{key: value})

    def test_custom_timeouts(self):
        c = self.load(MYSQL_CONNECT_TIMEOUT="3", MYSQL_READ_TIMEOUT="7", MYSQL_WRITE_TIMEOUT="9")
        self.assertEqual((c.mysql_connect_timeout, c.mysql_read_timeout, c.mysql_write_timeout), (3, 7, 9))

    def test_remote_production_without_ca_rejected(self):
        with self.assertRaises(RuntimeError):
            self.load(APP_ENV="production", APP_ORIGIN="https://example.com", MYSQL_HOST="db.example.com")

    def test_invalid_ca_rejected(self):
        with patch("config.Path.is_file", return_value=False), self.assertRaises(RuntimeError):
            self.load(MYSQL_SSL_CA="/mock/missing-ca.pem")

    def test_ca_verified_remote_config(self):
        with patch("config.Path.is_file", return_value=True):
            c = self.load(APP_ENV="production", APP_ORIGIN="https://example.com", MYSQL_HOST="db.example.com", MYSQL_SSL_CA="/mock/ca.pem")
        self.assertEqual(c.mysql_ssl_ca, "/mock/ca.pem")


class RetentionTests(unittest.TestCase):
    def test_plan_is_read_only_and_uses_utc_cutoff(self):
        db = MagicMock(spec=Database)
        db.one.return_value = {"quantidade": 3}
        now = datetime(2030, 2, 1, tzinfo=timezone(timedelta(hours=-3)))
        result = planejar_limpeza(db, 30, agora=now)
        db.one.assert_called_once_with(COUNT_EXPIRED, (datetime(2030, 1, 2, 3),))
        db.execute.assert_not_called()
        self.assertEqual(result["candidatas"], 3)
        self.assertEqual(result["modo"], "somente_leitura")

    def test_invalid_retention_never_queries(self):
        db = MagicMock(spec=Database)
        for value in (-1, 0, 6, 3651, True, "30"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                planejar_limpeza(db, value)
        db.one.assert_not_called()

    def test_naive_clock_rejected(self):
        with self.assertRaises(ValueError):
            planejar_limpeza(MagicMock(), agora=datetime(2030, 1, 1))


class LoginPersistenceContractTests(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock(spec=Database)
        now = datetime(2030, 1, 1)
        self.row = dict(id=1, nome="Synthetic", email="synthetic@example.com", perfil="padrao",
                        ativo=True, criado_em=now, atualizado_em=now, senha_hash="synthetic-hash")
        self.db.find_user.return_value = self.row.copy()
        self.client = TestClient(create_app(config(), self.db))
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        self.headers = {"origin": config().origin}

    def login(self):
        return self.client.post("/api/auth/login", json={"email":"synthetic@example.com", "senha":"synthetic-password"}, headers=self.headers)

    @patch("main.verify", return_value=True)
    def test_login_cookie_and_response_contract_preserved(self, verify):
        self.client.cookies.set("jadilson_session", "a" * 43)
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"usuario", "csrf_token"})
        self.assertEqual(set(response.json()["usuario"]), set(self.row) - {"senha_hash"})
        self.assertNotIn("synthetic-hash", response.text)
        self.assertNotIn("synthetic-password", response.text)
        cookie = response.headers["set-cookie"]
        for flag in ("HttpOnly", "SameSite=strict", "Path=/api", "Max-Age=3600"):
            self.assertIn(flag, cookie)
        from auth import digest
        args = self.db.create_session.call_args
        self.assertEqual(args.kwargs, {"previous_digest": digest("a" * 43)})
        self.assertEqual(len(args.args[0]), 64)
        self.assertEqual(len(args.args[2]), 64)
        self.db.revoke.assert_not_called()

    @patch("main.verify", return_value=True)
    def test_persistence_error_is_503_no_cookie_or_sensitive_error(self, verify):
        self.db.create_session.side_effect = mysql.connector.OperationalError("synthetic-sensitive", errno=2013)
        response = self.login()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("set-cookie", response.headers)
        self.assertNotIn("synthetic-sensitive", response.text)

    def test_expired_or_revoked_session_rejected(self):
        self.db.session.return_value = None
        self.client.cookies.set("jadilson_session", "a" * 43)
        self.assertEqual(self.client.get("/api/auth/session").status_code, 401)

    def test_restore_and_logout_contract(self):
        row = {k:v for k,v in self.row.items() if k != "senha_hash"}
        self.db.session.side_effect = lambda _: {**row, "csrf_token": "b" * 64}
        self.client.cookies.set("jadilson_session", "a" * 43)
        response = self.client.get("/api/auth/session")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["csrf_token"], "b" * 64)
        response = self.client.post("/api/auth/logout", json={}, headers={**self.headers, "X-CSRF-Token": "b" * 64})
        self.assertEqual(response.status_code, 204)
        self.db.revoke.assert_called_once()
        self.assertIn("Max-Age=0", response.headers["set-cookie"])


if __name__ == "__main__":
    unittest.main()
