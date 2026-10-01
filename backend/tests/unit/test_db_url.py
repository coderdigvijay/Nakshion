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


def test_ingest_url_is_neon_safe():
    """Regression (BUG-022): app.rag.ingest passed Neon's sslmode/channel_binding straight to asyncpg
    (TypeError: connect() got an unexpected keyword argument 'sslmode')."""
    from app.rag.ingest import _async_url

    url, extra = _async_url("postgresql://u:p@ep-x.ap-southeast-1.aws.neon.tech/db?sslmode=require&channel_binding=require")
    assert url.startswith("postgresql+asyncpg://")
    assert "sslmode" not in url and "channel_binding" not in url
    assert extra == {"ssl": "require"}
