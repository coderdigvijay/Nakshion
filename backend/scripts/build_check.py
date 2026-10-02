#!/usr/bin/env python3
"""Render build-time checks. Fails the build early (not at 3 a.m. at runtime) if:
- the Swiss Ephemeris data files are missing or pyswisseph would fall back to Moshier;
- the Alembic history is not a single linear head.
Optionally pre-downloads the embedding model into the build artifact (EMBEDDINGS_RUNTIME=local), because
Render's runtime disk is ephemeral and a boot-time download would cost ~70 MB and many seconds per cold start."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from app.astrology import ephemeris_self_check

    info = ephemeris_self_check()
    print(f"ephemeris ok: {info['ephemeris']} swe {info['swe_version']} path={info['ephe_path']}")

    from alembic.config import Config
    from alembic.script import ScriptDirectory

    heads = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini"))).get_heads()
    if len(heads) != 1:
        print(f"alembic has {len(heads)} heads: {heads}", file=sys.stderr)
        return 1
    print(f"alembic single head: {heads[0]}")

    # Prompt versions come ONLY from app/llm/prompts/registry.yaml (no env override), so the deployed
    # version is whatever is committed. Fail the build if a pinned template is missing or was edited in place.
    from app.llm.prompts import get_registry

    reg = get_registry()
    print("active prompts: " + ", ".join(f"{k}={v}" for k, v in reg.reg["active"].items()))

    if os.environ.get("EMBEDDINGS_RUNTIME", "local") == "local":
        from fastembed import TextEmbedding

        model = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
        TextEmbedding(model, cache_dir=os.environ.get("FASTEMBED_CACHE_PATH"), threads=1)
        print(f"embedding model cached: {model}")
    else:
        print("embeddings off: model not downloaded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
