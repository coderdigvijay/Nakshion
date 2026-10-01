"""Compatibility reports (api-contract.md section 8).

Scores are deterministic (engine); the LLM only writes narrative, with a template fallback,
so a report is always returned. Both chart ids are ownership-checked. Quota is pre-checked
before any work and consumed atomically in the same transaction as the report insert.
No DB transaction/lock is held while the engine or the LLM runs.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from app.core.security import user_id_hash
from app.models import BirthChart, CompatibilityReport, User
from app.schemas.compatibility import CompatibilityIn, CompatibilityReportOut
from app.services import ai, cache, chart_service, engine, quota_service

log = logging.getLogger("app.compat")

CATEGORY_KEYS = ("emotional", "communication", "romance", "passion", "long-term")
DEDUPE_WINDOW = timedelta(days=30)
METHOD_VERSION = "compat-1.0"


def _out(report: CompatibilityReport, partner_name: str) -> CompatibilityReportOut:
    return CompatibilityReportOut(
        id=report.id,
        chart1_id=report.chart1_id,
        chart2_id=report.chart2_id,
        relationship_type=report.relationship_type,
        overall_score=float(report.overall_score),
        compatibility_data=report.compatibility_data,
        partner_name=partner_name,
        created_at=report.created_at,
    )


def _clamp_score(v: Any) -> float:
    try:
        return round(min(10.0, max(0.0, float(v))), 1)
    except (TypeError, ValueError):
        return 5.0


def assemble(calc: dict[str, Any], narrative: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """Merge engine scores with narrative text into the frozen contract shape (2.4)."""
    cats_calc = calc.get("categories") or {}
    cats_text = narrative.get("categories") or {}
    categories = {
        k: {
            "score": _clamp_score((cats_calc.get(k) or {}).get("score", 5.0)),
            "summary": str((cats_text.get(k) or {}).get("summary") or ""),
        }
        for k in CATEGORY_KEYS
    }
    interps = list(narrative.get("aspect_interpretations") or [])
    aspects = []
    for i, a in enumerate((calc.get("synastry_aspects") or [])[:10]):
        aspects.append(
            {
                "planet1": str(a.get("planet1", "")),
                "planet2": str(a.get("planet2", "")),
                "aspect": str(a.get("aspect") or a.get("type") or ""),
                "orb": round(float(a.get("orb", 0) or 0), 2),
                "interpretation": str(interps[i]) if i < len(interps) else "",
            }
        )

    def three(xs: Any, filler: str) -> list[str]:
        out = [str(x) for x in (xs or [])][:3]
        while len(out) < 3:
            out.append(filler)
        return out

    data: dict[str, Any] = {
        "categories": categories,
        "synastry_aspects": aspects,
        "strengths": three(narrative.get("strengths"), "A willingness to understand each other"),
        "challenges": three(narrative.get("challenges"), "Different rhythms that need patience"),
        "summary": str(narrative.get("summary") or ""),
        "ashtakoota": calc.get("ashtakoota"),
        "manglik": calc.get("manglik"),
        "method_version": str(calc.get("method_version") or METHOD_VERSION),
        "approximate": bool(calc.get("approximate", False)),
        # engine 2.0: how the overall score was built (weights, blend, ranges when the Moon is ambiguous)
        "score_breakdown": calc.get("score_breakdown"),
    }
    return _clamp_score(calc.get("overall_score", 5.0)), data


async def _existing_report(
    db: AsyncSession, user_id: uuid.UUID, chart1_id: uuid.UUID, chart2_id: uuid.UUID, rel: str
) -> CompatibilityReport | None:
    return await db.scalar(
        select(CompatibilityReport)
        .where(
            CompatibilityReport.user_id == user_id,
            CompatibilityReport.chart1_id == chart1_id,
            CompatibilityReport.chart2_id == chart2_id,
            CompatibilityReport.relationship_type == rel,
            CompatibilityReport.created_at > datetime.now(UTC) - DEDUPE_WINDOW,
        )
        .order_by(CompatibilityReport.created_at.desc())
        .limit(1)
    )


async def create_report(db: AsyncSession, user: User, data: CompatibilityIn) -> tuple[CompatibilityReportOut, bool]:
    """Returns (report, created). created=False means an identical recent report was reused (200)."""
    chart1 = await chart_service.get_owned(db, user.id, data.chart1_id)                         # 1
    if not user.email_verified:
        raise Forbidden("Please verify your email to create compatibility reports.", code="EMAIL_NOT_VERIFIED")
    rel_label = "partner" if data.relationship_type == "romantic" else data.relationship_type
    partner_inputs = data.partner_inputs()

    await quota_service.precheck(db, user, quota_service.COMPAT_REPORT)
    chart1_data = chart1.chart_data
    chart1_id = chart1.id

    partner = await chart_service.find_or_create_partner(db, user, partner_inputs, rel_label)  # 2
    await db.commit()
    if partner.id == chart1_id:
        raise ValidationFailed("The partner details match the chart you selected. Please enter the other person's details.")
    existing = await _existing_report(db, user.id, chart1_id, partner.id, data.relationship_type)
    if existing is not None:
        return _out(existing, partner.name), False
    partner_data, partner_id, partner_name = partner.chart_data, partner.id, partner.name
    await db.commit()  # no transaction held during engine + LLM

    lock_key = f"lock:compat:{user.id}:{chart1_id}:{partner_id}:{data.relationship_type}"
    if not await cache.acquire_lock(lock_key, 60):
        # An identical request is already generating: wait for its report instead of duplicating work/quota.
        loop = asyncio.get_running_loop()
        end = loop.time() + 30
        while loop.time() < end:
            await asyncio.sleep(0.4)
            found = await _existing_report(db, user.id, chart1_id, partner_id, data.relationship_type)
            if found is not None:
                await db.commit()
                return _out(found, partner_name), False
            await db.commit()
        raise Conflict("This report is still being prepared. Please try again in a moment.", code="MESSAGE_IN_FLIGHT")
    try:
        existing = await _existing_report(db, user.id, chart1_id, partner_id, data.relationship_type)
        if existing is not None:  # a peer finished between our first check and taking the lock
            await db.commit()
            return _out(existing, partner_name), False
        await db.commit()
        calc = await engine.compute_compatibility(                                                  # 3
            chart1_data, partner_data, data.relationship_type,
            self_role=data.self_ashtakoota_role, partner_role=data.partner_ashtakoota_role,
        )
        narrative, generated_by = await ai.compat_narrative(calc, data.relationship_type)           # 4
        overall, compat_data = assemble(calc, narrative)
        compat_data["generated_by"] = generated_by

        report = CompatibilityReport(                                                               # 5
            user_id=user.id,
            chart1_id=chart1_id,
            chart2_id=partner_id,
            relationship_type=data.relationship_type,
            overall_score=overall,
            compatibility_data=compat_data,
        )
        db.add(report)
        await quota_service.consume(db, user, quota_service.COMPAT_REPORT)
        await db.commit()
        await db.refresh(report)
        log.info("compat_created", extra={"user": user_id_hash(user.id), "report_id": str(report.id)})
        return _out(report, partner_name), True
    finally:
        await cache.release_lock(lock_key)


async def list_reports(db: AsyncSession, user: User) -> list[CompatibilityReportOut]:
    rows = await db.execute(
        select(CompatibilityReport, BirthChart.name)
        .join(BirthChart, BirthChart.id == CompatibilityReport.chart2_id)
        .where(CompatibilityReport.user_id == user.id)
        .order_by(CompatibilityReport.created_at.desc())
        .limit(50)
    )
    return [_out(r, name) for r, name in rows]


async def get_report(db: AsyncSession, user: User, report_id: uuid.UUID) -> CompatibilityReportOut:
    row = (
        await db.execute(
            select(CompatibilityReport, BirthChart.name)
            .join(BirthChart, BirthChart.id == CompatibilityReport.chart2_id)
            .where(CompatibilityReport.id == report_id, CompatibilityReport.user_id == user.id)
        )
    ).first()
    if row is None:
        raise NotFound("Report not found.")
    return _out(row[0], row[1])


async def delete_report(db: AsyncSession, user: User, report_id: uuid.UUID) -> None:
    res = await db.execute(
        delete(CompatibilityReport).where(CompatibilityReport.id == report_id, CompatibilityReport.user_id == user.id)
    )
    if not res.rowcount:
        await db.rollback()
        raise NotFound("Report not found.")
    await db.commit()
