from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings

GOOD = dict(
    APP_ENV="production",
    DATABASE_URL="postgresql+asyncpg://u:p@ep-x-pooler.eu-central-1.aws.neon.tech/db?sslmode=require&channel_binding=require",
    REDIS_URL="rediss://default:p@eu1-x.upstash.io:6379",
    JWT_SECRET_KEY="j" * 40, CRON_SECRET="c" * 40, OTP_PEPPER="o" * 40,
    CORS_ORIGINS="https://nakshion.vercel.app", FRONTEND_URL="https://nakshion.vercel.app",
    API_PUBLIC_URL="https://nakshion-api.onrender.com",
    TRUSTED_PROXY_HOPS=1,
)


def make(**over) -> Settings:
    return Settings(_env_file=None, **{**GOOD, **over})


def test_good_production_config_boots() -> None:
    s = make()
    assert s.is_production and s.cors_origins_list == ["https://nakshion.vercel.app"]


@pytest.mark.parametrize(
    "over, needle",
    [
        ({"JWT_SECRET_KEY": "short"}, "JWT_SECRET_KEY"),
        ({"CRON_SECRET": ""}, "CRON_SECRET"),
        ({"OTP_PEPPER": "change-me"}, "OTP_PEPPER"),
        ({"CRON_SECRET": "j" * 40}, "must all be different"),
        ({"DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5432/db"}, "DATABASE_URL"),
        ({"DATABASE_URL": "postgresql+asyncpg://u:p@ep-x.neon.tech/db"}, "require TLS"),
        ({"REDIS_URL": "redis://localhost:6379/0"}, "REDIS_URL"),
        ({"REDIS_URL": "redis://default:p@eu1-x.upstash.io:6379"}, "rediss://"),
        ({"CORS_ORIGINS": "https://nakshion.vercel.app,http://localhost:5175"}, "CORS_ORIGINS"),
        ({"CORS_ORIGINS": "*"}, "CORS_ORIGINS"),
        ({"CORS_ORIGINS": "http://nakshion.vercel.app"}, "CORS_ORIGINS"),
        ({"FRONTEND_URL": "http://localhost:5175"}, "FRONTEND_URL"),
        ({"API_PUBLIC_URL": "http://nakshion-api.onrender.com"}, "API_PUBLIC_URL"),
        ({"RATE_LIMIT_ENABLED": False}, "RATE_LIMIT_ENABLED"),
        ({"TRUSTED_PROXY_HOPS": 0}, "TRUSTED_PROXY_HOPS"),
    ],
)
def test_unsafe_production_config_refuses_to_boot(over: dict, needle: str) -> None:
    with pytest.raises(ValidationError) as exc:
        make(**over)
    msg = str(exc.value)
    assert needle in msg
    assert "input_value" not in msg
    for secret in ("j" * 40, "c" * 40, "o" * 40, "u:p@", "jjjj", "cccc"):
        assert secret not in msg  # error text names settings, never values


def test_development_is_not_restricted() -> None:
    s = Settings(_env_file=None, APP_ENV="development", DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
                 JWT_SECRET_KEY="dev")
    assert not s.is_production


def test_api_docs_disabled_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings
    from app.main import create_app

    monkeypatch.setattr(settings, "APP_ENV", "production")
    app = create_app()
    assert app.docs_url is None and app.openapi_url is None and app.redoc_url is None


def test_plaintext_redis_only_with_explicit_private_network_flag() -> None:
    url = "redis://red-abc123:6379"
    with pytest.raises(ValidationError):
        make(REDIS_URL=url)
    assert make(REDIS_URL=url, REDIS_ALLOW_PLAINTEXT=True).is_production
    with pytest.raises(ValidationError):
        make(REDIS_URL="redis://localhost:6379", REDIS_ALLOW_PLAINTEXT=True)  # flag never legitimises localhost


def test_client_ip_header_can_replace_proxy_hops_in_production() -> None:
    assert make(TRUSTED_PROXY_HOPS=0, CLIENT_IP_HEADER="cf-connecting-ip").is_production
    with pytest.raises(ValidationError):
        make(CLIENT_IP_HEADER="bad header!")


def test_default_token_lifetime_is_two_days_and_build_version_is_short_sha() -> None:
    s = make(RENDER_GIT_COMMIT="0123456789abcdef")
    assert Settings.model_fields["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"].default == 2880  # class default (a local .env may override)
    assert s.build_version == "0123456"
