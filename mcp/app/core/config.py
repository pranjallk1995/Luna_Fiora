import base64
import os
from dataclasses import dataclass
from typing import ClassVar
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

@dataclass(frozen=True)
class AppConfig:
    GOOGLE_AUTH_URI: ClassVar[str] = "https://accounts.google.com/o/oauth2/auth"
    GOOGLE_TOKEN_URI: ClassVar[str] = "https://oauth2.googleapis.com/token"
    GMAIL_QUERY: ClassVar[str] = 'newer_than:45d (UPI OR debited OR credited OR transaction OR purchase OR EMI OR SIP)'
    GMAIL_MAX_RESULTS: ClassVar[int] = 100
    GOOGLE_STATE_MAX_AGE_SECONDS: ClassVar[int] = 900
    # Files one Drive folder import may hold, and the longest piece of a statement sent to the model.
    DRIVE_MAX_FILES: ClassVar[int] = 200
    STATEMENT_CHUNK_CHARS: ClassVar[int] = 6000
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
    google_client_id: str
    google_client_secret: str
    gmail_redirect_uri: str
    drive_redirect_uri: str
    encryption_key: str
    poll_seconds: int
    mcp_public_url: str = "http://localhost:18003"
    host: str = "0.0.0.0"
    port: int = 8000

    @staticmethod
    def derive_encryption_key(api_token):
        """A Fernet key derived from the API token; rotating the token means reconnecting Gmail and Drive."""
        key=HKDF(algorithm=hashes.SHA256(),length=32,salt=None,info=b"fiora-gmail-refresh-token").derive(api_token.encode())
        return base64.urlsafe_b64encode(key).decode()

    @classmethod
    def from_env(cls):
        token = os.environ.get("LUNAFIORA_API_TOKEN", "")
        if len(token) < 32:
            raise RuntimeError("LUNAFIORA_API_TOKEN must contain at least 32 characters")
        mcp_public_url = os.getenv("MCP_PUBLIC_URL", cls.mcp_public_url).strip().rstrip("/")
        return cls(
            database_url=os.environ["DATABASE_URL"], api_token=token,
            mcp_public_url=mcp_public_url,
            ollama_url=os.getenv("OLLAMA_URL", "http://luna-sentia-ollama:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen3-vl:8b-instruct"),
            google_client_id=os.getenv("GOOGLE_CLIENT_ID", "").strip(),
            google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "").strip(),
            gmail_redirect_uri=f"{mcp_public_url}/api/gmail/callback",
            drive_redirect_uri=f"{mcp_public_url}/api/drive/callback",
            encryption_key=cls.derive_encryption_key(token),
            poll_seconds=max(60, int(os.getenv("GMAIL_POLL_MINUTES", "15")) * 60),
        )