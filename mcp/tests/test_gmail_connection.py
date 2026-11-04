import os
import unittest
from contextlib import contextmanager
from unittest import mock
from cryptography.fernet import Fernet
from app.core.config import AppConfig
from app.integrations.gmail import GmailReader, GmailSignInExpired
from app.integrations.gmail_oauth import GmailOAuth
from app.services.gmail_import import GmailImportService

class FakeCursor:
    def __init__(self,db): self.db=db
    def execute(self,sql,params=()):
        if sql.startswith("DELETE FROM gmail_connections"): self.db.rows.clear()
        elif sql.startswith("INSERT INTO gmail_connections"): self.db.rows.append({"email":params[0],"encrypted_refresh_token":params[1],"last_sync_at":None})
        elif sql.startswith("UPDATE gmail_connections"): self.db.rows[0]["last_sync_at"]="now"
    def fetchone(self): return self.db.rows[0] if self.db.rows else None

class FakeDB:
    def __init__(self): self.rows=[]
    @contextmanager
    def cursor(self): yield FakeCursor(self)

class FakeOAuth:
    def exchange(self,url,state): return "me@example.com","refresh-token"

def service(reader=None,client_id="client"):
    reader=reader or mock.Mock(client_id=client_id,client_secret="secret")
    return GmailImportService(FakeDB(),reader,None,FakeOAuth(),Fernet.generate_key().decode())

class ConnectionTests(unittest.TestCase):
    def test_connecting_stores_an_encrypted_token(self):
        imports=service(); self.assertFalse(imports.status()["connected"])
        self.assertEqual(imports.connect("url","state"),"me@example.com")
        status=imports.status()
        self.assertEqual((status["connected"],status["email"],status["sign_in_expired"]),(True,"me@example.com",False))
        self.assertNotIn("refresh-token",imports.db.rows[0]["encrypted_refresh_token"])
    def test_a_new_sign_in_replaces_the_last(self):
        imports=service(); imports.save_connection("old@example.com","a"); imports.save_connection("new@example.com","b")
        self.assertEqual([row["email"] for row in imports.db.rows],["new@example.com"])
    def test_disconnecting_forgets_the_token(self):
        imports=service(); imports.connect("url","state"); imports.disconnect()
        self.assertFalse(imports.status()["connected"])
    def test_no_client_is_not_configured(self):
        self.assertFalse(service(client_id="").status()["configured"])
    def test_sync_without_a_connection_reads_nothing(self):
        imports=service(); result=imports.sync_all(None)
        self.assertEqual((result["configured"],result["connected"]),(True,False))
        imports.reader.messages.assert_not_called()

class ExpiredSignInTests(unittest.TestCase):
    def status_with(self,problem):
        imports=service(); imports.reader.account_email.side_effect=problem
        imports.connect("url","state"); return imports.status()
    def test_an_expired_sign_in_is_reported(self):
        self.assertTrue(self.status_with(GmailSignInExpired())["sign_in_expired"])
    def test_an_outage_does_not_look_like_a_lost_sign_in(self):
        self.assertFalse(self.status_with(ConnectionError("no network"))["sign_in_expired"])
    def test_no_connection_is_not_an_expiry(self):
        self.assertFalse(service().status()["sign_in_expired"])
    def test_a_token_that_cannot_be_read_is_an_expiry(self):
        imports=service(); imports.connect("url","state")
        imports.cipher=Fernet(Fernet.generate_key())
        self.assertTrue(imports.status()["sign_in_expired"])
        with self.assertRaises(GmailSignInExpired): imports.sync_all(None)
    def test_googles_answer_becomes_a_plain_message(self):
        from google.auth.exceptions import RefreshError
        from google.oauth2.credentials import Credentials
        with mock.patch("googleapiclient.discovery.build") as build:
            GmailReader("id","secret").service("refresh")
        credentials=build.call_args.kwargs["credentials"]
        with mock.patch.object(Credentials,"refresh",side_effect=RefreshError("invalid_grant: Token has been expired")):
            with self.assertRaises(GmailSignInExpired): credentials.refresh(None)

class OAuthTests(unittest.TestCase):
    def setUp(self):
        self.oauth=GmailOAuth("client","secret","https://fiora-mcp.example.test/api/gmail/callback","x"*32)
    def test_the_callback_survives_a_tls_terminating_proxy(self):
        self.assertEqual(self.oauth.callback_response("http://fiora-mcp.example.test/api/gmail/callback?code=abc&state=s"),
            "https://fiora-mcp.example.test/api/gmail/callback?code=abc&state=s")
    def test_the_state_names_who_started_it(self):
        url=self.oauth.authorization_url()
        self.assertIn("gmail.readonly",url); self.assertIn("access_type=offline",url); self.assertNotIn("code_challenge",url)
        state=self.oauth.signer.dumps({"purpose":"gmail","user":"owner"})
        self.assertEqual(self.oauth.user_of(state),"owner")
    def test_a_forged_state_is_refused(self):
        with self.assertRaises(PermissionError): self.oauth.user_of("forged")
    def test_no_client_cannot_start_a_sign_in(self):
        with self.assertRaisesRegex(ValueError,"GOOGLE_CLIENT_ID"): GmailOAuth("","","http://localhost/x","x"*32).authorization_url()

class KeyTests(unittest.TestCase):
    def test_the_key_comes_from_the_api_token(self):
        key=AppConfig.derive_encryption_key("t"*32)
        self.assertEqual(key,AppConfig.derive_encryption_key("t"*32)); self.assertNotEqual(key,AppConfig.derive_encryption_key("u"*32))
        Fernet(key.encode())
    def test_the_redirect_comes_from_the_public_address(self):
        env={"DATABASE_URL":"x","LUNAFIORA_API_TOKEN":"t"*32,"MCP_PUBLIC_URL":"https://fiora-mcp.example.test/"}
        with mock.patch.dict(os.environ,env): config=AppConfig.from_env()
        self.assertEqual(config.gmail_redirect_uri,"https://fiora-mcp.example.test/api/gmail/callback")
