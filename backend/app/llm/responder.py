"""Chat pipeline steps [1]-[8] of llm-integration.md §3 (persistence [9] is backend-elite's).

Streaming partial-message rule (ai_llm_rules §7): if the provider stream fails after the
first token, `stream()` raises LLMUnavailable and NOTHING is persisted; the caller emits an
SSE `error` event, releases the user's quota, and the UI shows its retry bubble. Only the
final ("done", result) event is persisted, so there is never a half-written row.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, replace
from datetime import date
from typing import Any, AsyncIterator, Protocol

from pydantic import ValidationError

from app.llm.builder import build_chat_prompt, repair_messages, sanitize_user_text
from app.llm.budget import BudgetGuard
from app.llm.errors import LLMError, LLMUnavailable
from app.llm.facts import ChartFacts, ChartIndex, build_chart_facts
from app.llm.lexicon import detect_timeframe, detect_topic
from app.llm.qtype import classify_question
from app.llm.router import LLMRouter
from app.llm.safety import canned_output, classify_input, distress_signals, static_reply
from app.llm.schemas import ChatAnswer, ChatMeta
from app.llm.labels import localize_label, with_system
from app.llm.textclean import BracketFilter, effective_language, deleak, detail_level, fix_terms, is_small_talk, neutralize_gender, strip_fact_ids, tidy_start, user_greeted
from app.llm.types import LLMResult
from app.llm.validators import Violation, strip_violating_sentences, validate_answer

log = logging.getLogger("nakshion.llm.chat")
META_DELIM = "<<<META>>>"
NO_NOTE_LINE = ("NO SOURCED NOTE: the reference library has no note that matches this question. Say so in one short clause "
                "(\"I don't have a sourced note on that\"), answer only from CHART FACTS or clearly hedged general knowledge "
                "(\"traditionally\", \"traditions differ\"), invent no specifics, and cite no reference notes.")


class Retriever(Protocol):
    """`retrieve_ex` (preferred, returns .chunks/.degraded/.reason/.stats) or plain `retrieve` (list)."""

    async def retrieve(self, *, kb_keys: list[str], question: str, system: str, topic: str,
                       language: str) -> list[Any]: ...


@dataclass(frozen=True)
class ChatInput:
    chart_data: dict
    question: str
    history: list[dict]
    language: str = "english"
    astrology_system: str = "both"
    user_id_hash: str | None = None
    user_id: str | None = None
    tier: str = "free"
    factors: list[Any] | None = None       # engine select_factors output, when available
    display_name: str = "the user"
    is_minor: bool = False
    today: date | None = None
    request_id: str | None = None


class ChatResponder:
    def __init__(self, router: LLMRouter, *, retriever: Retriever | None = None,
                 budget: BudgetGuard | None = None, deadline_s: float | None = None) -> None:
        self.router = router
        self.retriever = retriever
        self.budget = budget
        self.deadline_s = deadline_s or router.s.chat_deadline_s

    # ------------------------------------------------------------------ shared steps
    def _static(self, inp: ChatInput, cls: str) -> dict:
        text = static_reply(cls, inp.language)  # type: ignore[arg-type]
        return {"answer": text, "citations": [], "tokens_used": 0,
                "metadata": {"safety": cls, "generated_by": "static", "topic": "general",
                             "citations": [], "follow_ups": [], "validator_flags": []}}

    async def _prepare(self, inp: ChatInput, streaming: bool):
        q = sanitize_user_text(inp.question, self.router.s.max_user_message_chars)
        topic, timeframe = detect_topic(q), detect_timeframe(q)
        qt = classify_question(q)
        facts = build_chart_facts(inp.chart_data, factors=inp.factors, system=inp.astrology_system,
                                  display_name=inp.display_name, today=inp.today, is_minor=inp.is_minor,
                                  focus_planets=qt.planets[:3], k=7 if qt.is_general else 12)
        notes: list[Any] = []
        low_conf = False
        rag: dict[str, Any] = {"used": False, "degraded": False, "reason": None, "hits": 0, "low_confidence": False}
        if self.retriever is not None and not is_small_talk(q):
            keys = [k for f in facts.factors[:6] for k in f.kb_keys]
            kw = dict(kb_keys=keys, question=q, system=inp.astrology_system, topic=topic, language=inp.language)
            try:
                if hasattr(self.retriever, "retrieve_ex"):
                    r = await self.retriever.retrieve_ex(**kw)
                    notes = list(r.chunks)
                    rag.update(degraded=bool(r.degraded), reason=r.reason)
                    if getattr(r, "low_confidence", False) and not r.degraded:
                        low_conf = True
                        notes = []          # weak matches are not support: the model is told there is no sourced note
                else:
                    notes = list(await self.retriever.retrieve(**kw))
                rag.update(used=True, hits=len(notes))
            except Exception:  # noqa: BLE001 - graceful degradation to a chart-only answer
                log.exception("retrieval failed; answering from chart facts only")
                rag.update(used=True, degraded=True, reason="error")
        elif self.retriever is not None:
            rag.update(reason="small_talk")
        md = {"user_id": inp.user_id, "user_id_hash": inp.user_id_hash, "request_id": inp.request_id}
        req, prov = build_chat_prompt(facts=facts, notes=notes, history=inp.history, question=q,
                                      language=inp.language, streaming=streaming, metadata=md,
                                      max_user_chars=self.router.s.max_user_message_chars, qtype=qt)
        if low_conf:
            rag.update(low_confidence=True, hits=0)
            req = req.with_(context_blocks=req.context_blocks + (NO_NOTE_LINE,))
        prov.extra["rag"] = rag
        prov.extra["sources_available"] = [
            {"alias": a, "source_id": hashlib.sha1(cid.encode()).hexdigest()[:10],
             "title": getattr(n, "source_title", getattr(n, "file", "")),
             "section": n.heading_path.split(" > ")[-1][:80], "tier": (getattr(n, "meta", {}) or {}).get("tier")}
            for (a, cid), n in zip(prov.kb_aliases, notes)]
        hedge = tuple(a for (a, _cid), n in zip(prov.kb_aliases, notes)
                      if (getattr(n, "meta", None) or {}).get("unverified") or (getattr(n, "meta", None) or {}).get("schools_differ")
                      or (getattr(n, "meta", None) or {}).get("confidence") == "low")
        facts = replace(facts, kb_aliases=prov.kb_aliases, kb_hedge=hedge)
        models = None
        if self.budget is not None:
            decision = await self.budget.admit("chat", inp.tier)  # type: ignore[arg-type]
            if decision.max_output_tokens:
                req = req.with_(max_output_tokens=decision.max_output_tokens)
            if decision.use_daily_models:
                models = self.router.s.chain_for("daily_personal")
        return q, topic, timeframe, facts, ChartIndex.from_chart(inp.chart_data), req, prov, models

    @staticmethod
    def _parse(parsed: dict, facts: ChartFacts, allow_greeting: bool = False) -> ChatAnswer:
        """Validate, strip internal IDs (valid ones are kept as citations), drop boilerplate greetings and
        orphaned leading connectors."""
        ans = ChatAnswer.model_validate(parsed)
        text, found = strip_fact_ids(ans.answer)
        text = tidy_start(text, allow_greeting=allow_greeting)
        text = neutralize_gender(text)
        text = fix_terms(text)
        text = deleak(text)
        if text == ans.answer:
            return ans
        cites = list(dict.fromkeys([*ans.citations, *[f for f in found if f in facts.citable_ids]]))[:8]
        return ans.model_copy(update={"answer": text.strip() or ans.answer, "citations": cites})

    def _remaining(self, start: float) -> float:
        return self.deadline_s - (time.monotonic() - start)

    def _validate(self, ans: ChatAnswer, facts: ChartFacts, idx: ChartIndex, lang: str,
                  detail: str = "normal", question: str = "") -> list[Violation]:
        vs = validate_answer(ans.answer, ans.citations, ans.topic, facts=facts, idx=idx, language=lang, detail=detail,
                             question=question, qtype=classify_question(question))
        return [v for v in vs if v.kind != "length"]      # mild length drift is logged by the sweep, never repaired (latency)

    @staticmethod
    def _finalize(ans: ChatAnswer, result: LLMResult, facts: ChartFacts, prov, violations: list[Violation],
                  outcome: str, topic_rule: str, timeframe: str, latency_ms: int, language: str) -> dict:
        cites = [c for c in ans.citations if c in facts.factor_ids]
        kb_cited = [a for a in ans.citations if a in dict(facts.kb_aliases)]
        if ans.topic != topic_rule:
            log.info("topic_disagreement", extra={"rule": topic_rule, "llm": ans.topic})
        md = {
            **prov.as_metadata(),
            "citations": cites, "follow_ups": ans.follow_ups, "topic": topic_rule, "llm_topic": ans.topic,
            "timeframe": timeframe, "confidence": ans.confidence, "needs_birth_time": ans.needs_birth_time,
            "provider": result.provider, "model": result.model, "validator_flags": sorted({v.kind for v in violations}),
            "outcome": outcome, "latency_ms": latency_ms, "language": language, "generated_by": "llm",
            "kb_cited": [dict(facts.kb_aliases)[a] for a in kb_cited],
            "kb_hedge_provided": [dict(facts.kb_aliases)[a] for a in facts.kb_hedge if a in dict(facts.kb_aliases)],
            "kb_hedge_cited": [dict(facts.kb_aliases)[a] for a in kb_cited if a in facts.kb_hedge],
        }
        avail = {x["alias"]: x for x in prov.extra.get("sources_available", [])}
        sources = [{k: v for k, v in avail[a].items() if k != "alias"} for a in kb_cited if a in avail]
        return {
            "answer": ans.answer,
            "citations": [{"factor_id": c, "label": with_system(c, localize_label(c, facts.label_for(c) or c, language), language),
                           "label_en": facts.label_for(c) or c} for c in cites],
            "sources": sources,
            "tokens_used": result.input_tokens + result.output_tokens,
            "metadata": md,
        }

    async def _repair_or_fallback(self, req, draft_text: str, ans: ChatAnswer, result: LLMResult,
                                  violations: list[Violation], facts, idx, inp, start, models):
        """[8]: one repair on the same model, then sentence-strip / canned reply / next provider."""
        errors = [f"{v.kind}: {v.detail}" for v in violations]
        repaired_req = repair_messages(req, draft_text, errors)
        try:
            r2 = await self.router.generate(repaired_req, schema=ChatAnswer, models=[result.model],
                                            deadline_s=max(2.0, self._remaining(start)))
            a2 = self._parse(r2.parsed, facts, user_greeted(inp.question))
            v2 = self._validate(a2, facts, idx, inp.language, detail_level(inp.question), inp.question)
            if not v2:
                return a2, r2, violations, "repaired"
            ans, result, violations = a2, r2, v2
        except LLMError:
            log.warning("repair call failed")
        if violations and all(v.kind in ("style", "system", "hedge") for v in violations):
            return ans, result, violations, "repaired_soft"      # style nits never fail a reply (no 503)
        safety = [v for v in violations if v.kind.startswith("safety:")]
        if safety:
            cls = safety[0].kind.split(":", 1)[1]
            if distress_signals(inp.question):
                cls = "crisis"       # never answer a distressed message with a canned "I can't share how I'm set up"
            safe = ChatAnswer(answer=canned_output(cls, inp.language), citations=[], topic="general",  # type: ignore[arg-type]
                              follow_ups=[], confidence="low")
            return safe, result, violations, "canned"
        kinds = {v.kind for v in violations}
        if kinds <= {"claim", "time_unknown", "citation"}:
            text, kept = strip_violating_sentences(ans.answer, violations)
            cites = [c for c in ans.citations if c in facts.factor_ids]
            if kept > 0.6 and (cites or ans.topic == "general") and text:
                return ans.model_copy(update={"answer": text, "citations": cites, "confidence": "low"}), \
                    result, violations, "stripped"
        # next provider in the chain
        chain = models or self.router.s.chain_for("chat")
        rest = chain[chain.index(result.model) + 1:] if result.model in chain else []
        if rest and self._remaining(start) > 3:
            r3 = await self.router.generate(req, schema=ChatAnswer, models=rest,
                                            deadline_s=self._remaining(start))
            a3 = self._parse(r3.parsed, facts, user_greeted(inp.question))
            v3 = self._validate(a3, facts, idx, inp.language, detail_level(inp.question), inp.question)
            if not v3:
                return a3, r3, violations, "fallback"
        log.warning("chat_validation_failed", extra={"kinds": sorted(kinds), "details": [v.detail[:90] for v in violations[:6]]})
        raise LLMUnavailable("no answer passed validation")

    # ------------------------------------------------------------------ non-streaming
    async def answer(self, inp: ChatInput) -> dict:
        inp = replace(inp, language=effective_language(inp.question, inp.language))
        start = time.monotonic()
        cls = classify_input(inp.question)
        if cls:
            return self._static(inp, cls)
        q, topic, timeframe, facts, idx, req, prov, models = await self._prepare(inp, streaming=False)
        result = await self.router.generate(req, schema=ChatAnswer, models=models, deadline_s=self.deadline_s)
        ans = self._parse(result.parsed, facts, user_greeted(inp.question))
        violations = self._validate(ans, facts, idx, inp.language, detail_level(inp.question), inp.question)
        first_flags = sorted({v.kind for v in violations})
        outcome = "ok"
        if violations:
            ans, result, violations, outcome = await self._repair_or_fallback(
                req, result.text, ans, result, violations, facts, idx, inp, start, models)
        out = self._finalize(ans, result, facts, prov, violations, outcome, topic, timeframe,
                             int((time.monotonic() - start) * 1000), inp.language)
        out["metadata"]["first_draft_flags"] = first_flags
        return out

    # ------------------------------------------------------------------ streaming
    async def stream(self, inp: ChatInput) -> AsyncIterator[tuple[str, Any]]:
        inp = replace(inp, language=effective_language(inp.question, inp.language))
        start = time.monotonic()
        cls = classify_input(inp.question)
        if cls:
            res = self._static(inp, cls)
            yield ("delta", res["answer"])
            yield ("done", res)
            return
        q, topic, timeframe, facts, idx, req, prov, models = await self._prepare(inp, streaming=True)
        buf = ""
        emitted = 0
        final: LLMResult | None = None
        hold = len(META_DELIM)
        clean = BracketFilter()      # fact IDs / [KB:..] markers never reach the client
        async for chunk in self.router.stream(req, models=models, deadline_s=self.deadline_s):
            if chunk.final is not None:
                final = chunk.final
                continue
            buf += chunk.text
            cut = buf.find(META_DELIM)
            safe_end = cut if cut >= 0 else max(emitted, len(buf) - hold)
            if safe_end > emitted:
                text = clean.feed(buf[emitted:safe_end])
                emitted = safe_end
                if text:
                    yield ("delta", text)
        if final is None:
            raise LLMUnavailable("stream ended without a final result")
        raw_answer, delim, meta_text = buf.partition(META_DELIM)
        if emitted < len(raw_answer):
            tail = clean.feed(raw_answer[emitted:])
            if tail:
                yield ("delta", tail)
        tail = clean.flush()
        if tail:
            yield ("delta", tail)
        answer_text, found_ids = strip_fact_ids(raw_answer)
        answer_text = answer_text.strip()
        meta: ChatMeta | None = None
        if delim and meta_text.strip():
            try:
                meta = ChatMeta.model_validate(json.loads(meta_text.strip().strip("`").removeprefix("json")))
            except (ValueError, ValidationError):
                meta = None
        # A stream is only "complete" when the provider stopped normally AND the META block parsed.
        # Anything else (length cut, dropped connection, missing/garbled META) is never persisted as ok:
        # regenerate through the structured path and tell the UI to replace the partial text.
        complete = final.finish_reason == "stop" and meta is not None and bool(answer_text)
        outcome = "ok"
        first_flags: list[str] = []
        if complete:
            try:
                ans = ChatAnswer(answer=answer_text, **meta.model_dump())  # type: ignore[union-attr]
            except ValidationError:
                complete = False
        if complete:
            cites = list(dict.fromkeys([*ans.citations, *[f for f in found_ids if f in facts.factor_ids]]))[:8]
            ans = ans.model_copy(update={"citations": cites})
            violations = self._validate(ans, facts, idx, inp.language, detail_level(inp.question), inp.question)
            first_flags = sorted({v.kind for v in violations})
            if violations:
                sreq, _ = build_chat_prompt(facts=facts, notes=[], history=inp.history, question=q,
                                            language=inp.language, streaming=False, metadata=req.metadata)
                sreq = sreq.with_(context_blocks=req.context_blocks)
                ans, final, violations, outcome = await self._repair_or_fallback(
                    sreq, answer_text, ans, replace(final, text=answer_text), violations, facts, idx, inp, start, models)
                yield ("replace", ans.answer)
        else:
            log.warning("stream_incomplete", extra={"finish_reason": final.finish_reason, "has_meta": meta is not None,
                                                    "chars": len(answer_text)})
            first_flags = ["incomplete_stream"]
            sreq, _ = build_chat_prompt(facts=facts, notes=[], history=inp.history, question=q,
                                        language=inp.language, streaming=False, metadata=req.metadata)
            sreq = sreq.with_(context_blocks=req.context_blocks)
            # Raises LLMUnavailable if no complete, valid answer can be produced: nothing is persisted.
            result = await self.router.generate(sreq, schema=ChatAnswer, models=models,
                                                deadline_s=max(5.0, self._remaining(start)))
            ans = self._parse(result.parsed, facts, user_greeted(inp.question))
            violations = self._validate(ans, facts, idx, inp.language, detail_level(inp.question), inp.question)
            final, outcome = result, "regenerated"
            if violations:
                ans, final, violations, outcome = await self._repair_or_fallback(
                    sreq, result.text, ans, result, violations, facts, idx, inp, start, models)
            yield ("replace", ans.answer)
        out = self._finalize(ans, final, facts, prov, violations, outcome, topic, timeframe,
                             int((time.monotonic() - start) * 1000), inp.language)
        out["metadata"]["first_draft_flags"] = first_flags
        yield ("done", out)
