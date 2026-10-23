from cryptography.fernet import Fernet
from app.integrations.gmail import deterministic_extract
from app.core.models import TransactionInput

class GmailImportService:
    def __init__(self,db,reader,extractor,key):
        self.db=db; self.reader=reader; self.extractor=extractor
        self.cipher=Fernet(key.encode()) if key else None
    @property
    def configured(self): return bool(self.reader.client_id and self.reader.client_secret and self.cipher)
    def save_connection(self,email,refresh_token):
        if not self.configured: raise ValueError("Gmail OAuth is not configured")
        encrypted=self.cipher.encrypt(refresh_token.encode()).decode()
        with self.db.cursor() as c:
            c.execute("""INSERT INTO gmail_connections(email,encrypted_refresh_token) VALUES(%s,%s)
            ON CONFLICT(email) DO UPDATE SET encrypted_refresh_token=EXCLUDED.encrypted_refresh_token""",(email,encrypted))
    def sync_all(self,finance):
        if not self.configured: return {"configured":False,"imported":0,"review":0}
        with self.db.cursor() as c: c.execute("SELECT * FROM gmail_connections"); connections=c.fetchall()
        imported=review=0
        for connection in connections:
            token=self.cipher.decrypt(connection["encrypted_refresh_token"].encode()).decode()
            for message in self.reader.messages(token):
                with self.db.cursor() as c:
                    c.execute("SELECT 1 FROM gmail_imports WHERE message_id=%s",(message["id"],))
                    if c.fetchone(): continue
                item=deterministic_extract(message)
                if item is None:
                    try:
                        raw=self.extractor.extract(message["subject"],message["body"])
                        if raw:
                            raw.update({"source":"gmail","external_id":message["id"],"notes":"Imported from Gmail using local Ollama"})
                            item=TransactionInput.model_validate(raw).model_dump()
                    except Exception: item=None
                transaction=None
                if item:
                    transaction=finance.repo.create("transactions",TransactionInput.model_validate(item).model_dump()); imported+=1
                else: review+=1
                with self.db.cursor() as c:
                    c.execute("""INSERT INTO gmail_imports(message_id,email,subject,sender,received_at,status,excerpt,transaction_id)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                    (message["id"],connection["email"],message["subject"],message["sender"],message["received_at"],
                     "imported" if transaction else "review",message["body"][:500],transaction["id"] if transaction else None))
            with self.db.cursor() as c: c.execute("UPDATE gmail_connections SET last_sync_at=NOW() WHERE email=%s",(connection["email"],))
        return {"configured":True,"imported":imported,"review":review}