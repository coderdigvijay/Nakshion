from __future__ import annotations

from app.db.session import prepare_url


def test_neon_url_params_translated_for_asyncpg() -> None:
    url, extra = prepare_url("postgresql://u:p@ep-x-pooler.eu.aws.neon.tech/db?sslmode=require&channel_binding=require")
    assert url == "postgresql+asyncpg://u:p@ep-x-pooler.eu.aws.neon.tech/db"
    assert extra == {"ssl": "require"}


def test_plain_local_url_untouched_and_other_params_kept() -> None:
    url, extra = prepare_url("postgresql+asyncpg://u:p@localhost:5432/astroai?application_name=nakshion")
    assert url.endswith("/astroai?application_name=nakshion") and extra == {}
    url, extra = prepare_url("postgres://u:p@h/db?sslmode=disable")
    assert url == "postgresql+asyncpg://u:p@h/db" and extra == {}
