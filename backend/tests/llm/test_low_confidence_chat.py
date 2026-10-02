"""Trap query end to end: a retrieval result flagged low_confidence must not reach the model as notes."""

from __future__ import annotations

from app.llm.config import LLMSettings
from app.llm.providers.fake import FakeProvider
from app.llm.responder import NO_NOTE_LINE, ChatInput, ChatResponder
from app.llm.router import LLMRouter
from app.rag.retriever import RetrievalResult, RetrievedChunk

from .conftest import TODAY, chat_json
from .test_responder_service import Dispatch

TRAP = "Explain the Varshaphal Muntha progression rules for my solar return year."
ANS = ("I don't have a sourced note on Muntha progression, so I can only speak in general terms. Traditionally it is a yearly "
       "progressed point, and traditions differ on how it is read. " + "Your chart can still frame the year with patience. " * 3)


def chunk():
    return RetrievedChunk("x#1", "x.md", "H", "vedic", "Unrelated text about Saturn.", (), 0.02, (), {}, ("f:t",))


class Retr:
    def __init__(self, low, chunks):
        self.low, self.chunks, self.calls = low, chunks, 0

    async def retrieve_ex(self, **kw):
        self.calls += 1
        return RetrievalResult(self.chunks, low_confidence=self.low)


def resp(retr, answers):
    s = LLMSettings(_env_file=None, LLM_MODEL_CHAT="fake-primary", LLM_FALLBACK_CHAT="", retry_backoff_ms=(0, 0))
    p = FakeProvider([chat_json(a, c, topic="general") for a, c in answers])
    return ChatResponder(LLMRouter(s, {"fake": Dispatch(**{"fake-primary": p})}), retriever=retr), p


async def test_low_confidence_drops_notes_adds_the_line_and_hides_sources(chart):
    r, p = resp(Retr(True, [chunk()]), [(ANS, ["V.MD.SATURN"])])
    res = await r.answer(ChatInput(chart_data=chart, question=TRAP, history=[], today=TODAY, astrology_system="vedic"))
    ctx = p.calls[0][0].context_blocks
    assert ctx[-1] == NO_NOTE_LINE and not any(b.startswith("REFERENCE NOTES") for b in ctx)
    md = res["metadata"]
    assert md["rag"]["low_confidence"] is True and md["rag"]["hits"] == 0
    assert res["sources"] == [] and md["kb_cited"] == []


async def test_confident_retrieval_is_unchanged(chart):
    r, p = resp(Retr(False, [chunk()]), [(ANS, ["V.MD.SATURN"])])
    res = await r.answer(ChatInput(chart_data=chart, question=TRAP, history=[], today=TODAY, astrology_system="vedic"))
    ctx = p.calls[0][0].context_blocks
    assert NO_NOTE_LINE not in ctx and any(b.startswith("REFERENCE NOTES") for b in ctx)
    assert res["metadata"]["rag"]["low_confidence"] is False
