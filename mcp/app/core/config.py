import os
from dataclasses import dataclass
from typing import ClassVar

@dataclass(frozen=True)
class AppConfig:
    GOOGLE_AUTH_URI: ClassVar[str] = "https://accounts.google.com/o/oauth2/auth"
    GOOGLE_TOKEN_URI: ClassVar[str] = "https://oauth2.googleapis.com/token"
    GMAIL_QUERY: ClassVar[str] = 'newer_than:45d (UPI OR debited OR credited OR transaction OR purchase OR EMI OR SIP)'
    GMAIL_MAX_RESULTS: ClassVar[int] = 100
    GMAIL_STATE_MAX_AGE_SECONDS: ClassVar[int] = 900
    # The context every Luna app requests for Sentia's shared model; Ollama reloads a
    # model whose context changes, so a different value swaps it out for the others.
    OLLAMA_CONTEXT_TOKENS: ClassVar[int] = 16384
    OLLAMA_TIMEOUT_SECONDS: ClassVar[float] = 90.0
    # Longest part of an email body sent to the model.
    EMAIL_BODY_CHARS: ClassVar[int] = 5000
    DB_POOL_MAX_SIZE: ClassVar[int] = 8

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