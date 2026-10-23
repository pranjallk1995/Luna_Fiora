from mcp.server.fastmcp import FastMCP
from app.core.config import AppConfig
from app.data.database import Database
from app.data.repositories import FinanceRepository
from app.integrations.gmail import GmailReader
from app.integrations.gmail_oauth import GmailOAuth
from app.integrations.ollama import OllamaExtractor
from app.services.application import FioraService
from app.services.gmail_import import GmailImportService
from app.services.workers import GmailWorker
from app.transport.http_routes import FioraHTTPRoutes
from app.transport.mcp_tools import FioraMCPTools

class LunaFioraApplication:
    def __init__(self,config):
        self.config=config; self.db=Database(config.database_url); self.db.open(); self.db.initialize()
        self.service=FioraService(FinanceRepository(self.db))
        reader=GmailReader(config.gmail_client_id,config.gmail_client_secret)
        extractor=OllamaExtractor(config.ollama_url,config.ollama_model)
        self.imports=GmailImportService(self.db,reader,extractor,config.encryption_key)
        self.oauth=GmailOAuth(config.gmail_client_id,config.gmail_client_secret,config.gmail_redirect_uri,config.api_token)
        self.mcp=FastMCP("LunaFiora",host=config.host,port=config.port,stateless_http=True,json_response=True)
        FioraMCPTools(self.mcp,self.service,self.imports)
        FioraHTTPRoutes(self.mcp,self.service,self.imports,self.oauth,config.api_token)
        self.worker=GmailWorker(self.imports,self.service,config.poll_seconds); self.worker.start()
    def run(self):
        try:self.mcp.run(transport="streamable-http")
        finally:self.worker.stop(); self.db.close()

application=LunaFioraApplication(AppConfig.from_env())
mcp=application.mcp
app=mcp.streamable_http_app()
if __name__=="__main__": application.run()