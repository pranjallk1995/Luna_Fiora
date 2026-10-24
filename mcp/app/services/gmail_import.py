from cryptography.fernet import Fernet
from app.services.import_graph import MessageImportGraph

class GmailImportService:
    def __init__(self,db,reader,extractor,key):
        self.db=db; self.reader=reader; self.extractor=extractor; self.graph=MessageImportGraph(db,extractor)
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
        counts={"imported":0,"review":0,"skipped":0}
        for connection in connections:
            token=self.cipher.decrypt(connection["encrypted_refresh_token"].encode()).decode()
            for message in self.reader.messages(token):
                counts[self.graph.run(message,finance,connection["email"])]+=1
            with self.db.cursor() as c: c.execute("UPDATE gmail_connections SET last_sync_at=NOW() WHERE email=%s",(connection["email"],))
        return {"configured":True,"imported":counts["imported"],"review":counts["review"]}