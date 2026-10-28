import os
from dataclasses import dataclass

@dataclass(frozen=True)
class AppConfig:
    database_url: str
    api_token: str
    ollama_url: str
    ollama_model: str
    gmail_client_id: str
    gmail_client_secret: str
    gmail_redirect_uri: str
    encryption_key: str
    poll_seconds: int
    host: str = "0.0.0.0"
    port: int = 8000

    @classmethod
    def from_env(cls):
        token = os.environ.get("LUNAFIORA_API_TOKEN", "")
        if len(token) < 32:
            raise RuntimeError("LUNAFIORA_API_TOKEN must contain at least 32 characters")
        return cls(
            database_url=os.environ["DATABASE_URL"], api_token=token,
            ollama_url=os.getenv("OLLAMA_URL", "http://luna-sentia-ollama:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen3-vl:8b-instruct"),
            gmail_client_id=os.getenv("GMAIL_CLIENT_ID", ""),
            gmail_client_secret=os.getenv("GMAIL_CLIENT_SECRET", ""),
            gmail_redirect_uri=os.getenv("GMAIL_REDIRECT_URI", "http://localhost:18003/api/gmail/callback"),
            encryption_key=os.getenv("FIORA_TOKEN_ENCRYPTION_KEY", ""),
            poll_seconds=max(60, int(os.getenv("GMAIL_POLL_MINUTES", "15")) * 60),
        )