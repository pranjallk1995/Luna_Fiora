"""Validated settings for the UI gateway and the browser app it serves."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlparse


@dataclass(frozen=True)
class SSOConfig:
    """Single sign-on through Luna Sentia; this block is identical in every Luna app's config.py."""

    COOKIE_NAME: ClassVar[str] = "luna_sso"
    SESSION_HEADER: ClassVar[str] = "X-Luna-Session"
    # How long a confirmed session is trusted before asking Sentia again, so a sign-out
    # in another app takes effect here within this many seconds.
    RECHECK_SECONDS: ClassVar[int] = 60
    LOOKUP_TIMEOUT_SECONDS: ClassVar[float] = 5.0
    SESSION_CACHE_ENTRIES: ClassVar[int] = 256

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
    """Immutable gateway settings."""

    UI_ROOT: ClassVar[Path] = Path(__file__).resolve().parent
    # The release this image holds, shown in the footer and on Luna Unia's cards.
    VERSION: ClassVar[str] = os.getenv("LUNA_VERSION", "").strip()
    # The built React app; the Dockerfile puts it here.
    STATIC_DIR: ClassVar[Path] = UI_ROOT / "static"
    # A Gmail sync reads every new message, which can take a while.
    API_TIMEOUT_SECONDS: ClassVar[float] = 90.0
    MAX_REQUEST_BYTES: ClassVar[int] = 1024 * 1024
    # Hashed bundles never change under the same name.
    IMMUTABLE_CACHE_CONTROL: ClassVar[str] = "private, max-age=31536000, immutable"
    CONTENT_SECURITY_POLICY: ClassVar[str] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    )

    api_url: str
    api_token: str
    allowed_emails: frozenset[str]
    sso: SSOConfig

    @classmethod
    def from_env(cls) -> "UIConfig":
        """Build and validate gateway configuration from environment variables."""
        api_url = os.getenv("LUNAFIORA_API_URL", "http://luna-fiora-mcp:8000").rstrip("/")
        parsed = urlparse(api_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RuntimeError("LUNAFIORA_API_URL must be a valid HTTP(S) URL.")
        api_token = os.getenv("LUNAFIORA_API_TOKEN", "").strip()
        if not api_token:
            raise RuntimeError("LUNAFIORA_API_TOKEN must be set.")
        allowed_emails = frozenset(
            email.strip().casefold()
            for email in os.getenv("LUNAFIORA_ALLOWED_EMAILS", "").split(",")
            if email.strip()
        )
        if not allowed_emails:
            raise RuntimeError("LUNAFIORA_ALLOWED_EMAILS must list at least one account.")
        return cls(api_url=api_url, api_token=api_token, allowed_emails=allowed_emails, sso=SSOConfig.from_env())
