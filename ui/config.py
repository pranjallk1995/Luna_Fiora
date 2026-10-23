import os
from dataclasses import dataclass
@dataclass(frozen=True)
class UIConfig:
    api_url:str; api_token:str; allowed_emails:frozenset[str]
    @classmethod
    def from_env(cls):
        emails=frozenset(x.strip().casefold() for x in os.environ["LUNAFIORA_ALLOWED_EMAILS"].split(",") if x.strip())
        return cls(os.getenv("LUNAFIORA_API_URL","http://luna-fiora-mcp:8000").rstrip("/"),os.environ["LUNAFIORA_API_TOKEN"],emails)