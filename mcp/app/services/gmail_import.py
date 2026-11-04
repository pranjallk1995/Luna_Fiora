import logging
from cryptography.fernet import Fernet, InvalidToken
from app.integrations.gmail import GmailSignInExpired
from app.services.import_graph import MessageImportGraph

logger=logging.getLogger(__name__)

class GmailImportService:
    def __init__(self,db,reader,extractor,oauth,key):
        self.db=db; self.reader=reader; self.extractor=extractor; self.oauth=oauth; self.graph=MessageImportGraph(db,extractor)
        self.cipher=Fernet(key.encode())
    @property
    def configured(self): return bool(self.reader.client_id and self.reader.client_secret)
    def connection(self):
        with self.db.cursor() as c:
            c.execute("SELECT * FROM gmail_connections ORDER BY created_at DESC LIMIT 1"); return c.fetchone()
    def status(self):
        connection=self.connection()
        return {"configured":self.configured,"connected":connection is not None,
                "email":connection["email"] if connection else None,
                "last_sync_at":connection["last_sync_at"] if connection else None,
                "sign_in_expired":connection is not None and self.sign_in_expired(connection)}
    def sign_in_expired(self,connection):
        """Ask Google whether the saved sign-in still works; other trouble is not an expiry."""
        try: self.reader.account_email(self.token(connection))
        except GmailSignInExpired: return True
        except Exception as error:  # An outage must not look like a lost sign-in.
            logger.warning("Could not check the Gmail sign-in: %s",type(error).__name__)
        return False
    def token(self,connection):
        try: return self.cipher.decrypt(connection["encrypted_refresh_token"].encode()).decode()
        except InvalidToken as error:
            raise GmailSignInExpired("The saved Gmail sign-in cannot be read. Reconnect Gmail from Fiora's overview to continue; your transactions are safe.") from error
    def connect(self,url,state):
        email,refresh_token=self.oauth.exchange(url,state); self.save_connection(email,refresh_token)
        return email
    def save_connection(self,email,refresh_token):
        """Each person connects one account: a new sign-in replaces the last."""
        encrypted=self.cipher.encrypt(refresh_token.encode()).decode()
        with self.db.cursor() as c:
            c.execute("DELETE FROM gmail_connections")
            c.execute("INSERT INTO gmail_connections(email,encrypted_refresh_token) VALUES(%s,%s)",(email,encrypted))
    def disconnect(self):
        """Forget the saved sign-in; transactions and the record of imported messages stay."""
        with self.db.cursor() as c: c.execute("DELETE FROM gmail_connections")
        return {"status":"disconnected"}
    def sync_all(self,finance):
        if not self.configured: return {"configured":False,"connected":False,"imported":0,"review":0}
        connection=self.connection()
        if connection is None: return {"configured":True,"connected":False,"imported":0,"review":0}
        counts={"imported":0,"review":0,"skipped":0}
        for message in self.reader.messages(self.token(connection)):
            counts[self.graph.run(message,finance,connection["email"])]+=1
        with self.db.cursor() as c: c.execute("UPDATE gmail_connections SET last_sync_at=NOW() WHERE email=%s",(connection["email"],))
        return {"configured":True,"connected":True,"imported":counts["imported"],"review":counts["review"]}
