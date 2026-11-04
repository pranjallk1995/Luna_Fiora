from app.core.config import AppConfig
from app.data.database import Database
from app.core import tenancy
from app.data.repositories import DriveImportRepository, FinanceRepository
from app.integrations.drive import DriveOAuth
from app.integrations.gmail import GmailReader
from app.integrations.gmail_oauth import GmailOAuth
from app.integrations.ollama import OllamaExtractor
from app.services.application import FioraService
from app.services.drive_import import DriveImportService
from app.services.gmail_import import GmailImportService
from app.services.workers import GmailWorker
from app.transport.http_routes import FioraHTTPRoutes
from app.transport.luna_mcp import LunaMCP
from app.transport.mcp_tools import FioraMCPTools

class LunaFioraApplication:
    def __init__(self,config):
        self.config=config; self.db=Database(config.database_url); self.db.open(); self.db.initialize()
        self.service=FioraService(FinanceRepository(self.db))
        reader=GmailReader(config.google_client_id,config.google_client_secret)
        extractor=OllamaExtractor(config.ollama_url,config.ollama_model)
        oauth=GmailOAuth(config.google_client_id,config.google_client_secret,config.gmail_redirect_uri,config.api_token)
        self.imports=GmailImportService(self.db,reader,extractor,oauth,config.encryption_key)
        self.drive=DriveImportService(DriveImportRepository(self.db),
            DriveOAuth(config.google_client_id,config.google_client_secret,config.drive_redirect_uri,config.api_token),extractor,config.encryption_key)
        for user_id in self.db.tenants.users():
            with tenancy.acting_as(user_id): self.drive.resume()
        self.mcp=LunaMCP("LunaFiora",app="fiora",remove_user=self.db.tenants.remove,public_url=config.mcp_public_url,api_token=config.api_token,open_paths=("/api/gmail/callback","/api/drive/callback"),
            host=config.host,port=config.port,stateless_http=True,json_response=True)
        FioraMCPTools(self.mcp,self.service,self.imports,self.drive)
        FioraHTTPRoutes(self.mcp,self.service,self.imports,self.drive,config.api_token)
        self.worker=GmailWorker(self.imports,self.service,config.poll_seconds,self.db.tenants.users); self.worker.start()
    def run(self):
        try:self.mcp.run(transport="streamable-http")
        finally:self.worker.stop(); self.db.close()

application=LunaFioraApplication(AppConfig.from_env())
mcp=application.mcp
app=mcp.streamable_http_app()
if __name__=="__main__": application.run()