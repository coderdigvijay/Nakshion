#!/usr/bin/env python3
"""One-off bulk upgrade of stored charts whose engine major is older than the running engine.

    python scripts/recompute_charts.py [--dry-run] [--batch 50]

Charts are also upgraded lazily on read (chart_service.get_chart / list_charts, max 5 per list);
this script covers charts nobody opens. Inputs come from the stored birth data; derived caches are
invalidated per chart. Run against a database you intend to change (it uses DATABASE_URL)."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import BirthChart  # noqa: E402
from app.services import chart_service, engine  # noqa: E402


async def main(dry_run: bool, batch: int) -> None:
    current = engine.major(engine.engine_version())
    done = failed = 0
    async with SessionLocal() as db:
        ids = [
            (cid, ver)
            for cid, ver in (await db.execute(select(BirthChart.id, BirthChart.engine_version))).all()
        ]
    stale = [cid for cid, ver in ids if engine.major(ver) < current]
    print(f"{len(stale)} of {len(ids)} charts below engine major {current}")
    if dry_run:
        return
    for i in range(0, len(stale), batch):
        for cid in stale[i : i + batch]:
            async with SessionLocal() as db:
                chart = await db.get(BirthChart, cid)
                before = chart.engine_version
                await chart_service._upgrade(db, chart)
                (done, failed) = (done + 1, failed) if chart.engine_version != before else (done, failed + 1)
    print(f"upgraded={done} failed={failed}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--batch", type=int, default=50)
    a = ap.parse_args()
    asyncio.run(main(a.dry_run, a.batch))
