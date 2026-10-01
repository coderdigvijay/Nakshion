"""Optional local cross-encoder reranker (fastembed ONNX). Loaded lazily; never imported at app start.

Decision (measured, see docs/rag-runbook.md): reranking is OFF by default unless the eval shows a gain
inside the memory/latency budget. This module exists so the decision is data-driven and reversible.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

log = logging.getLogger("nakshion.rag.rerank")


class CrossEncoderReranker:
    def __init__(self, model: str = "Xenova/ms-marco-MiniLM-L-6-v2", *, threads: int | None = 1, max_chars: int = 900):
        self.model_name = model
        self._threads = threads
        self._max = max_chars
        self._m: Any = None
        self._lock = threading.Lock()

    def _load(self):
        with self._lock:
            if self._m is None:
                from fastembed.rerank.cross_encoder import TextCrossEncoder

                self._m = TextCrossEncoder(self.model_name, threads=self._threads)
        return self._m

    async def score(self, query: str, docs: list[str]) -> list[float]:
        def run() -> list[float]:
            return [float(s) for s in self._load().rerank(query, [d[: self._max] for d in docs])]

        return await asyncio.to_thread(run)
