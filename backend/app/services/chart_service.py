"""Birth charts: create / list / get / update / delete / set-primary (api-contract.md section 5).

Rules owned here (single source):
- timezone is ALWAYS resolved server-side from lat/lon (G-05); the client value is a hint.
- one primary chart per user: flip in one transaction, backed by uq_birth_charts_one_primary.
- list order is contractual: is_primary DESC, created_at ASC (G-07).
- chart limits are checked under a per-user row lock (no count-then-insert race).
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from app.core.security import user_id_hash
from app.models import BirthChart, PersonalReading, User
from app.schemas.chart import BirthChartOut, BirthInputs, CreateChartIn
from app.services import cache, engine

log = logging.getLogger("app.charts")

LAZY_UPGRADES_PER_LIST = 5


# ------------------------------------------------------------------ computation (shared)
@dataclass
class ComputedChart:
    timezone: str
    time_of_birth: time | None
    has_exact_time: bool
    chart_data: dict[str, Any]
    engine_version: str


async def compute(inputs: BirthInputs) -> ComputedChart:
    """Resolve tz server-side, enforce the date ceiling, run the engine. No DB access."""
    tz = await engine.resolve_timezone(inputs.latitude, inputs.longitude)
    if inputs.timezone and inputs.timezone != tz:
        log.info("tz_mismatch", extra={"client_tz": inputs.timezone, "server_tz": tz})
    today_there = datetime.now(UTC).astimezone(ZoneInfo(tz)).date()
    if inputs.date_of_birth > today_there:
        raise ValidationFailed("Birth date cannot be in the future.", code="DATE_OUT_OF_RANGE")
    has_exact = inputs.has_exact_time and inputs.time_of_birth is not None
    data = await engine.compute_natal_chart(
        date_of_birth=inputs.date_of_birth,
        time_of_birth=inputs.time_of_birth,
        has_exact_time=has_exact,
        latitude=inputs.latitude,
        longitude=inputs.longitude,
        timezone=tz,
        dst_fold=inputs.dst_fold,
        utc_offset_override=inputs.utc_offset_override,
    )
    version = str((data.get("metadata") or {}).get("engine_version") or engine.engine_version())
    return ComputedChart(tz, inputs.time_of_birth, has_exact, data, version)


# ------------------------------------------------------------------ serialisation
async def to_out(chart: BirthChart, *, refresh: bool = True) -> BirthChartOut:
    data = chart.chart_data
    if refresh:
        data = await engine.refresh_time_dependent(data)
    return BirthChartOut(
        id=chart.id,
        user_id=chart.user_id,
        name=chart.name,
        relationship_label=chart.relationship,
        date_of_birth=chart.date_of_birth,
        time_of_birth=chart.time_of_birth,
        has_exact_time=chart.has_exact_time,
        birth_place_name=chart.birth_place_name,
        latitude=float(chart.latitude),
        longitude=float(chart.longitude),
        timezone=chart.timezone,
        chart_data=data,
        is_primary=chart.is_primary,
        created_at=chart.created_at,
        updated_at=chart.updated_at,
    )


# ------------------------------------------------------------------ ownership (single source)
async def get_owned(db: AsyncSession, user_id: uuid.UUID, chart_id: uuid.UUID, *, for_update: bool = False) -> BirthChart:
    stmt = select(BirthChart).where(BirthChart.id == chart_id, BirthChart.user_id == user_id)
    if for_update:
        stmt = stmt.with_for_update()
    chart = await db.scalar(stmt)
    if chart is None:
        raise NotFound("Chart not found.")
    return chart


async def get_primary(db: AsyncSession, user_id: uuid.UUID) -> BirthChart | None:
    """The user's own chart that drives chat and the personal reading. Only a chart labelled 'self'
    qualifies, so a saved person (partner, friend...) can never be mistaken for "my chart"."""
    return await db.scalar(
        select(BirthChart)
        .where(BirthChart.user_id == user_id, BirthChart.relationship == "self")
        .order_by(BirthChart.is_primary.desc(), BirthChart.created_at.asc())
        .limit(1)
    )


PRIMARY_MUST_BE_SELF = "Only your own chart can be your primary chart."


def _primary_error() -> ValidationFailed:
    return ValidationFailed(PRIMARY_MUST_BE_SELF, code="PRIMARY_MUST_BE_SELF")


async def _drop_personal_readings(db: AsyncSession, chart_id: uuid.UUID) -> None:
    """Stored personal readings were generated from this chart's data: remove them with the data
    (same transaction), otherwise the next read would serve a reading about the OLD chart."""
    await db.execute(delete(PersonalReading).where(PersonalReading.chart_id == chart_id))


def chart_limit(user: User) -> int:
    return settings.CHART_LIMIT_PREMIUM if user.subscription_tier == "premium" else settings.CHART_LIMIT_FREE


async def _lock_user_and_count(db: AsyncSession, user: User) -> int:
    # Serialises chart creation per user (limit + first-chart-is-primary decisions).
    await db.execute(select(User.id).where(User.id == user.id).with_for_update())
    return int(await db.scalar(select(func.count()).select_from(BirthChart).where(BirthChart.user_id == user.id)) or 0)


def _limit_error(user: User) -> Forbidden:
    return Forbidden(
        f"You've reached the limit of {chart_limit(user)} charts on your plan.", code="CHART_LIMIT_REACHED"
    )


async def _clear_primary(db: AsyncSession, user_id: uuid.UUID, except_id: uuid.UUID | None = None) -> None:
    stmt = update(BirthChart).where(BirthChart.user_id == user_id, BirthChart.is_primary.is_(True))
    if except_id is not None:
        stmt = stmt.where(BirthChart.id != except_id)
    await db.execute(stmt.values(is_primary=False))


async def _has_self_chart(db: AsyncSession, user_id: uuid.UUID, except_id: uuid.UUID | None = None) -> bool:
    stmt = select(BirthChart.id).where(BirthChart.user_id == user_id, BirthChart.relationship == "self")
    if except_id is not None:
        stmt = stmt.where(BirthChart.id != except_id)
    return (await db.scalar(stmt.limit(1))) is not None


async def invalidate(chart_id: uuid.UUID, user_id: uuid.UUID, *, was_primary: bool) -> None:
    """Delete everything derived from a chart. Call AFTER commit (caching_rules.md section 2).

    One SCAN pattern covers chart_summary:*, factors:*, transits:* and compat:* keys (all embed the
    chart id), instead of five separate scans: fewer billed Upstash commands."""
    await cache.delete_pattern(f"*{chart_id}*")
    if was_primary:
        await cache.delete_pattern(f"daily_personal:{user_id}:*")


# ------------------------------------------------------------------ C1 create
async def create_chart(db: AsyncSession, user: User, data: CreateChartIn) -> BirthChartOut:
    # Cheap pre-check so an over-limit user doesn't burn engine CPU.
    if int(await db.scalar(select(func.count()).select_from(BirthChart).where(BirthChart.user_id == user.id)) or 0) >= chart_limit(user):
        raise _limit_error(user)
    await db.commit()  # end the read txn (releases the connection; commit does not expire `user`)

    computed = await compute(data)

    existing = await _lock_user_and_count(db, user)
    if existing >= chart_limit(user):
        err = _limit_error(user)
        await db.rollback()
        raise err
    wants_primary = data.is_primary or existing == 0
    if data.relationship:
        relationship = data.relationship
    elif wants_primary:
        relationship = "self"  # the primary chart is, by definition, the user's own
    else:
        relationship = "other"
    if data.is_primary and relationship != "self":
        await db.rollback()
        raise _primary_error()
    make_primary = wants_primary and relationship == "self"  # a first chart for someone else is simply not primary
    if make_primary:
        await _clear_primary(db, user.id)
    chart = BirthChart(
        user_id=user.id,
        name=data.name,
        relationship=relationship,
        date_of_birth=data.date_of_birth,
        time_of_birth=computed.time_of_birth,
        has_exact_time=computed.has_exact_time,
        birth_place_name=data.birth_place_name,
        latitude=data.latitude,
        longitude=data.longitude,
        timezone=computed.timezone,
        chart_data=computed.chart_data,
        is_primary=make_primary,
        engine_version=computed.engine_version,
    )
    db.add(chart)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise Conflict("Another chart change happened at the same time. Please try again.") from None
    await db.refresh(chart)
    if make_primary:
        await cache.delete_pattern(f"daily_personal:{user.id}:*")
    log.info("chart_created", extra={"user": user_id_hash(user.id), "chart_id": str(chart.id)})
    return await to_out(chart)


# ------------------------------------------------------------------ lazy upgrade (C3)
def _needs_upgrade(chart: BirthChart) -> bool:
    if not engine.engine_available():
        return False
    stored = (chart.chart_data.get("metadata") or {}).get("engine_version") or chart.engine_version
    return engine.major(stored) < engine.major(engine.engine_version())


async def _upgrade(db: AsyncSession, chart: BirthChart) -> None:
    inputs = BirthInputs.model_construct(
        name=chart.name,
        date_of_birth=chart.date_of_birth,
        time_of_birth=chart.time_of_birth,
        has_exact_time=chart.has_exact_time,
        birth_place_name=chart.birth_place_name,
        latitude=float(chart.latitude),
        longitude=float(chart.longitude),
        timezone=chart.timezone,
        dst_fold=None,
        utc_offset_override=None,
    )
    try:
        computed = await compute(inputs)
    except Exception:  # noqa: BLE001 - keep serving the stored chart
        log.warning("lazy_upgrade_failed", extra={"chart_id": str(chart.id)})
        return
    chart.chart_data = computed.chart_data
    chart.engine_version = computed.engine_version
    chart.timezone = computed.timezone
    chart.updated_at = datetime.now(UTC)
    await _drop_personal_readings(db, chart.id)
    await db.commit()
    await invalidate(chart.id, chart.user_id, was_primary=chart.is_primary)


# ------------------------------------------------------------------ C2 / C3 read
async def list_charts(db: AsyncSession, user: User, relationship: str | None = None) -> list[BirthChartOut]:
    stmt = (
        select(BirthChart)
        .where(BirthChart.user_id == user.id)
        .order_by(BirthChart.is_primary.desc(), BirthChart.created_at.asc(), BirthChart.id.asc())
        .limit(settings.CHART_LIMIT_PREMIUM)
    )
    if relationship:
        stmt = stmt.where(BirthChart.relationship == relationship)
    charts = list(await db.scalars(stmt))
    upgraded = 0
    for c in charts:
        if upgraded < LAZY_UPGRADES_PER_LIST and _needs_upgrade(c):
            await _upgrade(db, c)
            upgraded += 1
    return [await to_out(c) for c in charts]


async def get_chart(db: AsyncSession, user: User, chart_id: uuid.UUID) -> BirthChartOut:
    chart = await get_owned(db, user.id, chart_id)
    if _needs_upgrade(chart):
        await _upgrade(db, chart)
    return await to_out(chart)


# ------------------------------------------------------------------ C4 update
async def update_chart(db: AsyncSession, user: User, chart_id: uuid.UUID, data: CreateChartIn) -> BirthChartOut:
    await get_owned(db, user.id, chart_id)  # 404 before spending CPU
    await db.commit()
    computed = await compute(data)
    chart = await get_owned(db, user.id, chart_id, for_update=True)
    was_primary = chart.is_primary
    if data.relationship:
        chart.relationship = data.relationship
    if (data.is_primary or chart.is_primary) and chart.relationship != "self":
        await db.rollback()
        raise _primary_error()
    if data.is_primary and not chart.is_primary:
        await _clear_primary(db, user.id, except_id=chart.id)
        chart.is_primary = True
    chart.name = data.name
    chart.date_of_birth = data.date_of_birth
    chart.time_of_birth = computed.time_of_birth
    chart.has_exact_time = computed.has_exact_time
    chart.birth_place_name = data.birth_place_name
    chart.latitude = data.latitude  # type: ignore[assignment]
    chart.longitude = data.longitude  # type: ignore[assignment]
    chart.timezone = computed.timezone
    chart.chart_data = computed.chart_data
    chart.engine_version = computed.engine_version
    chart.updated_at = datetime.now(UTC)
    await _drop_personal_readings(db, chart.id)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise Conflict("Another chart change happened at the same time. Please try again.") from None
    await db.refresh(chart)
    await invalidate(chart.id, user.id, was_primary=was_primary or chart.is_primary)
    log.info("chart_updated", extra={"user": user_id_hash(user.id), "chart_id": str(chart.id)})
    return await to_out(chart)


# ------------------------------------------------------------------ C5 delete
async def delete_chart(db: AsyncSession, user: User, chart_id: uuid.UUID) -> None:
    await db.execute(select(User.id).where(User.id == user.id).with_for_update())
    chart = await get_owned(db, user.id, chart_id, for_update=True)
    was_primary = chart.is_primary
    await _drop_personal_readings(db, chart.id)
    await db.delete(chart)
    await db.flush()
    if was_primary:
        # Only another of the user's OWN charts may take over; saved people never become primary.
        successor = await db.scalar(
            select(BirthChart)
            .where(BirthChart.user_id == user.id, BirthChart.relationship == "self")
            .order_by(BirthChart.created_at.asc())
            .limit(1)
        )
        if successor is not None:
            successor.is_primary = True
    await db.commit()
    await invalidate(chart_id, user.id, was_primary=was_primary)
    log.info("chart_deleted", extra={"user": user_id_hash(user.id), "chart_id": str(chart_id)})


# ------------------------------------------------------------------ C6 set primary
async def set_primary(db: AsyncSession, user: User, chart_id: uuid.UUID) -> BirthChartOut:
    chart = await get_owned(db, user.id, chart_id, for_update=True)
    if chart.relationship != "self":
        await db.rollback()
        raise _primary_error()
    if not chart.is_primary:
        await _clear_primary(db, user.id, except_id=chart.id)
        chart.is_primary = True
        chart.updated_at = datetime.now(UTC)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise Conflict("Another chart change happened at the same time. Please try again.") from None
        await db.refresh(chart)
        await cache.delete_pattern(f"daily_personal:{user.id}:*")
    return await to_out(chart)


# ------------------------------------------------------------------ partner charts (compatibility)
def _partner_query(user_id: uuid.UUID, inputs: BirthInputs):  # noqa: ANN202
    stmt = select(BirthChart).where(
        BirthChart.user_id == user_id,
        func.lower(BirthChart.name) == inputs.name.lower(),
        BirthChart.date_of_birth == inputs.date_of_birth,
        func.round(BirthChart.latitude, 3) == round(inputs.latitude, 3),
        func.round(BirthChart.longitude, 3) == round(inputs.longitude, 3),
    )
    stmt = stmt.where(
        BirthChart.time_of_birth.is_(None) if inputs.time_of_birth is None else BirthChart.time_of_birth == inputs.time_of_birth
    )
    return stmt.order_by(BirthChart.created_at.asc()).limit(1)


async def find_or_create_partner(
    db: AsyncSession, user: User, inputs: BirthInputs, relationship: str
) -> BirthChart:
    """Dedupe key: (user, lower(name), dob, tob, round(lat,3), round(lon,3)) (api-contract K1 step 2).

    Race-free without a unique index: the second lookup runs under the per-user row lock that also
    serialises chart creation, so two identical concurrent requests cannot both insert."""
    existing = await db.scalar(_partner_query(user.id, inputs))
    if existing is not None:
        return existing
    await db.commit()  # release the connection during CPU work
    computed = await compute(inputs)
    count = await _lock_user_and_count(db, user)
    existing = await db.scalar(_partner_query(user.id, inputs))  # re-check under the lock
    if existing is not None:
        return existing
    if count >= chart_limit(user):
        err = _limit_error(user)
        await db.rollback()
        raise err
    chart = BirthChart(
        user_id=user.id,
        name=inputs.name,
        relationship=relationship,
        date_of_birth=inputs.date_of_birth,
        time_of_birth=computed.time_of_birth,
        has_exact_time=computed.has_exact_time,
        birth_place_name=inputs.birth_place_name,
        latitude=inputs.latitude,
        longitude=inputs.longitude,
        timezone=computed.timezone,
        chart_data=computed.chart_data,
        is_primary=False,  # chart1 is owned, so this is never the first chart
        engine_version=computed.engine_version,
    )
    db.add(chart)
    await db.flush()
    return chart
