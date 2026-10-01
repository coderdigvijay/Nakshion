"""Application settings (pydantic-settings).

Secrets have no in-code defaults. ``JWT_SECRET_KEY`` and ``DATABASE_URL`` are required;
production additionally refuses example/weak values for JWT, cron and OTP secrets.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from pydantic import Field, field_validator, model_validator
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

# Export .env into the process env (without overriding real env vars) so sibling packages
# with their own settings (app.llm.LLMSettings reads os.environ only) see the same values.
load_dotenv(BACKEND_DIR / ".env", override=False)

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
_EXAMPLE_SECRETS = {"", "change-me", "changeme", "your-secret-key", "secret", "..."}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"), env_file_encoding="utf-8", extra="ignore",
        hide_input_in_errors=True,  # validation errors must never echo secret values into logs
    )

    # App
    APP_NAME: str = "Nakshion"
    APP_ENV: str = "development"
    APP_VERSION: str = "dev"
    FRONTEND_URL: str = "http://localhost:5175"
    API_PUBLIC_URL: str = "http://localhost:8010"
    CORS_ORIGINS: str = "http://localhost:5175,http://localhost:5173,http://localhost:3000"
    SOURCE_CODE_URL: str = ""

    # Data
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    # Render Key Value (free) is reachable only on Render's private network and speaks plain redis://.
    # Set true ONLY with that internal URL; Upstash and any public Redis must use rediss://.
    REDIS_ALLOW_PLAINTEXT: bool = False
    # "redis" (default): LLM spend/quota counters live in Redis (survive restarts, ~10 commands per LLM call).
    # "memory": in-process counters (0 Redis commands; reset on restart). Emergency lever for the Upstash cap.
    LLM_BUDGET_COUNTERS: str = Field(default="redis", pattern="^(redis|memory)$")
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5
    DB_COMMAND_TIMEOUT_S: float = 15.0  # web requests only; ingest/migrations use their own connections
    MIGRATION_DATABASE_URL: str = ""  # Neon direct (unpooled) endpoint for alembic

    # Auth
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080
    BCRYPT_ROUNDS: int = 12
    OTP_PEPPER: str = ""
    CRON_SECRET: str = ""

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # External services
    LOCATIONIQ_API_KEY: str = ""
    GEOAPIFY_API_KEY: str = ""
    GEOCODER_FALLBACK: str = "geoapify"
    BREVO_API_KEY: str = ""
    EMAIL_SENDER_ADDRESS: str = ""  # must be a Brevo-verified sender
    EMAIL_SENDER_NAME: str = "Nakshion"

    # Number of trusted reverse proxies in front of the app (Render: 1). 0 = use the socket peer.
    # The client IP is the entry N hops from the RIGHT of X-Forwarded-For (never the spoofable left side).
    TRUSTED_PROXY_HOPS: int = Field(default=0, ge=0, le=5)
    MAX_BODY_BYTES: int = 65536

    # Product
    DEFAULT_ANON_TZ: str = "Asia/Kolkata"
    RATE_LIMIT_ENABLED: bool = True

    # Quotas (architecture.md section 7)
    QUOTA_CHAT_FREE: int = 5
    QUOTA_CHAT_PREMIUM: int = 60
    QUOTA_COMPAT_FREE: int = 3
    QUOTA_COMPAT_PREMIUM: int = 50
    CHART_LIMIT_FREE: int = 10
    CHART_LIMIT_PREMIUM: int = 100

    CHAT_DEADLINE_S: float = 25.0

    @field_validator("JWT_ALGORITHM")
    @classmethod
    def _only_hs256(cls, v: str) -> str:
        if v != "HS256":
            raise ValueError("Only HS256 is supported")
        return v

    @model_validator(mode="after")
    def _production_guard(self) -> "Settings":
        """Refuse to boot in production with unsafe config. Messages name settings, never values."""
        if self.APP_ENV.lower() != "production":
            return self
        problems: list[str] = []

        def weak(val: str) -> bool:
            return val.strip().lower() in _EXAMPLE_SECRETS or len(val) < 32

        secrets_ = {"JWT_SECRET_KEY": self.JWT_SECRET_KEY, "CRON_SECRET": self.CRON_SECRET, "OTP_PEPPER": self.OTP_PEPPER}
        problems += [f"{k} is missing, an example value, or shorter than 32 characters" for k, v in secrets_.items() if weak(v)]
        if len({v for v in secrets_.values() if v}) < len([v for v in secrets_.values() if v]):
            problems.append("JWT_SECRET_KEY, CRON_SECRET and OTP_PEPPER must all be different values")
        if not self.RATE_LIMIT_ENABLED:
            problems.append("RATE_LIMIT_ENABLED cannot be false")

        db = urlsplit(self.DATABASE_URL)
        if not db.hostname or db.hostname in _LOCAL_HOSTS:
            problems.append("DATABASE_URL must point at a remote database (not localhost)")
        elif not _wants_tls(db.query):
            problems.append("DATABASE_URL must require TLS (add ?sslmode=require)")
        redis = urlsplit(self.REDIS_URL)
        if not redis.hostname or redis.hostname in _LOCAL_HOSTS:
            problems.append("REDIS_URL must point at a remote Redis (not localhost)")
        elif redis.scheme != "rediss" and not self.REDIS_ALLOW_PLAINTEXT:
            problems.append("REDIS_URL must use rediss:// (TLS), or set REDIS_ALLOW_PLAINTEXT for Render's private Key Value")

        origins = self.cors_origins_list
        if not origins:
            problems.append("CORS_ORIGINS must list the frontend origin(s)")
        for o in origins:
            u = urlsplit(o)
            if o == "*" or u.scheme != "https" or (u.hostname or "") in _LOCAL_HOSTS or u.path not in ("", "/"):
                problems.append("CORS_ORIGINS entries must be exact https origins (no wildcard, no localhost, no path)")
                break
        for name in ("FRONTEND_URL", "API_PUBLIC_URL"):
            u = urlsplit(getattr(self, name))
            if u.scheme != "https" or (u.hostname or "") in _LOCAL_HOSTS:
                problems.append(f"{name} must be a public https URL")
        if problems:
            raise ValueError("Refusing production boot: " + "; ".join(problems))
        return self

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def otp_pepper(self) -> str:
        # Dev fallback derives from the JWT secret so OTP hashes are still keyed.
        return self.OTP_PEPPER or ("otp:" + self.JWT_SECRET_KEY)

    @property
    def google_redirect_uri(self) -> str:
        return f"{self.API_PUBLIC_URL.rstrip('/')}/api/v1/auth/oauth/google/callback"


def _wants_tls(query: str) -> bool:
    q = dict(parse_qsl(query))
    return (q.get("sslmode") or q.get("ssl") or "").lower() in {"require", "verify-ca", "verify-full", "true", "1"}


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
