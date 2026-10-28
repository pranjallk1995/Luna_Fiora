import os
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class SSOConfig:
    """Single sign-on through Luna Sentia; this block is identical in every Luna app's config.py."""

    COOKIE_NAME: ClassVar[str] = "luna_sso"
    SESSION_HEADER: ClassVar[str] = "X-Luna-Session"
    # How long a confirmed session is trusted before asking Sentia again, so a sign-out
    # in another app takes effect here within this many seconds.
    RECHECK_SECONDS: ClassVar[int] = 60
    LOOKUP_TIMEOUT_SECONDS: ClassVar[float] = 5.0

    public_url: str
    internal_url: str = "http://luna-sentia-auth:8000"

    @classmethod
    def from_env(cls) -> "SSOConfig":
        public_url = os.getenv("LUNA_SSO_URL", "").strip().rstrip("/")
        if not public_url:
            raise RuntimeError("LUNA_SSO_URL must be the public address of Luna Sentia's auth service.")
        internal_url = os.getenv("LUNA_SSO_INTERNAL_URL", "").strip().rstrip("/")
        return cls(public_url=public_url, internal_url=internal_url or cls.internal_url)


@dataclass(frozen=True)
class UIConfig:
    api_url:str; api_token:str; allowed_emails:frozenset[str]; sso:SSOConfig
    api_timeout:float=90.0
    @classmethod
    def from_env(cls):
        emails=frozenset(x.strip().casefold() for x in os.environ["LUNAFIORA_ALLOWED_EMAILS"].split(",") if x.strip())
        return cls(os.getenv("LUNAFIORA_API_URL","http://luna-fiora-mcp:8000").rstrip("/"),os.environ["LUNAFIORA_API_TOKEN"],emails,SSOConfig.from_env())
