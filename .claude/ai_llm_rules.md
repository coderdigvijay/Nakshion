# AI / LLM / RAG Rules - Provider Abstraction, Grounding, Cost, Safety

Owner: `ai-genai-specialist`. Changes to prompts, safety policy, or token budgets are **T2**.

The model is a narrator, not a calculator. Swiss Ephemeris computes the chart
(`astrology_accuracy_rules.md`). RAG supplies reference text. The LLM writes the
interpretation of those two inputs and nothing else.

## 1. One provider interface. Nothing else imports an SDK.

The provider is currently Google Gemini and is under evaluation. Switching it must be a config
change plus one adapter file.

```
backend/app/services/llm/          (target layout)
  base.py        # LLMProvider protocol + LLMRequest / LLMResult / LLMChunk dataclasses
  gemini.py      # GeminiProvider - the ONLY file that imports the Gemini SDK
  fake.py        # FakeProvider - deterministic, used by tests and local dev without keys
  factory.py     # get_llm() reads settings.LLM_PROVIDER / LLM_MODEL
  budget.py      # token + request accounting, per-user and global caps
```

```python
class LLMProvider(Protocol):
    async def generate(self, req: LLMRequest) -> LLMResult: ...
    def stream(self, req: LLMRequest) -> AsyncIterator[LLMChunk]: ...

@dataclass(frozen=True)
class LLMRequest:
    system: str
    messages: list[Message]            # role + content, provider-neutral
    max_output_tokens: int
    temperature: float = 0.7
    response_schema: type[BaseModel] | None = None   # structured output
    prompt_id: str = ""                # e.g. "chat.system@3"
    timeout_s: float = 30.0

@dataclass(frozen=True)
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    provider: str
    finish_reason: str                 # "stop" | "length" | "safety" | "error"
```

- Routers and other services call `get_llm()`. A `import google.generativeai` (or any vendor
  SDK) outside `services/llm/<provider>.py` is a bug.
- Provider-specific behaviour (system-instruction placement, safety-setting names, key
  rotation, retry on 429) lives inside the adapter. Known Gemini gotchas:
  `.claude/knowledge/Astrology/backend/gemini-api-gotchas.md`. `google-generativeai` is
  deprecated in favour of `google-genai`. A rebuilt adapter should target the maintained SDK.
- Map vendor errors to a small set of internal exceptions (`LLMTimeout`, `LLMRateLimited`,
  `LLMUnavailable`, `LLMBlocked`). Raw SDK exceptions never cross the adapter boundary.
- Model names come from config, never string literals scattered through services.

## 2. Prompts are versioned files

- Prompts live in `backend/app/prompts/` (target layout), one file per prompt, with an id
  and an integer version (`chat_system.v3.md`, `daily_reading.v2.md`). Builders in
  `services/prompt_builder.py` fill them. No prompt strings inline in services.
- A prompt edit bumps its version. Never edit a released version in place.
- Persist provenance on every generated row: `messages.metadata` (JSONB, already in the
  schema) stores `{prompt_id, model, provider, rag_chunk_ids, chart_engine_version}`, and
  `messages.tokens_used` stores the token count. Daily readings store the same in their row.
- Cache keys for generated content include the prompt version and model
  (`caching_rules.md`), so a prompt change cannot serve old-prompt output.

## 3. Grounding: chart first, RAG second, model memory last

Context order inside every interpretation prompt:
1. **Safety and role rules** (system).
2. **CHART FACTS**: a compact, machine-generated block from `chart_data`, including system,
   ayanamsa, house system and `time_unknown`. This is authoritative.
3. **REFERENCE KNOWLEDGE**: top-k RAG chunks, labelled with source file and section.
4. Conversation history (windowed) and the user's message.

Rules stated in the system prompt and enforced in review:
- "Use only the positions in CHART FACTS. If a placement is not listed, say you do not have it.
  Never infer or compute a position."
- "If REFERENCE KNOWLEDGE contradicts CHART FACTS, CHART FACTS wins."
- If `time_unknown` is true, give no house, Ascendant, or MC interpretation.
- Name the system when naming a sign ("your tropical Sun in Leo").
- For structured outputs, reference placements by key (`"planet": "mars"`) and the server
  renders the sign and degree from `chart_data`. The model never emits a degree that reaches
  the UI.

## 4. Structured output is validated

- Any output the code parses (daily readings, compatibility summaries, titles, categories)
  uses `response_schema` plus Pydantic validation. Validation failure leads to one retry with the
  error appended, then a static fallback or a clear error. Never `json.loads` and hope.
- Bound every field: max lengths, enums for categories, numeric ranges for scores. Scores
  shown to users (for example `compatibility_reports.overall_score`) are **computed by code**
  from chart data, not invented by the model.
- `finish_reason == "length"` is a failure for structured output, not a truncated success.

## 5. RAG (local embeddings, ChromaDB)

- Embeddings are local (all-MiniLM-L6-v2 via chromadb or sentence-transformers). There are no
  embedding API calls. See `knowledge/Astrology/backend/rag-pipeline-pattern.md`.
- Pin the embedding model name and store it in collection metadata. Changing it means
  re-embedding the whole knowledge base. Mixed-model vectors are a silent quality bug.
- Chunk on markdown headers. Store `source`, `section`, and a content hash per chunk.
  Re-index on hash change only.
- Query enhancement adds the user's relevant placements (for example "Moon in Scorpio, 8th
  house") to the retrieval query. Retrieval is filtered by system (`vedic_*` vs Western
  sources) when the chart's system is known.
- Retrieval failure degrades to a chart-only answer and is logged. The chat still works.
- `backend/data/chroma_db/` is gitignored and rebuilt. `chromadb` and the embedding package must
  be pinned in `requirements.txt` (on 2026-10-01 `sentence-transformers` was installed in the
  venv but missing from requirements).

## 6. Cost and quota budgets (free tier is the default)

- Every call goes through `budget.py`: per-user daily request and token caps by
  `subscription_tier`, plus a **global daily cap** that switches generation off (the feature
  shows a friendly "busy" state) before the provider quota is exhausted for everyone.
- Hard limits per request: max input characters per user message (for example 2,000), conversation
  history window (last N turns or a token cap, with older turns summarised), `max_output_tokens`
  per prompt type.
- Log every call: `user_id`, `prompt_id`, `model`, input/output tokens, latency, finish reason.
  Never log the prompt body or birth data at INFO.
- Cache anything deterministic per input (daily readings per sign, base chart overview per chart
  plus engine version plus prompt version). Never generate the same daily reading twice.
- Batch scheduled work (daily readings for 12 signs x systems) once per day, with a lock so
  concurrent requests do not each trigger generation (`caching_rules.md`, stampede).
- Increments of usage counters are atomic in the DB or Redis (`INCR` with expiry, or
  `UPDATE ... RETURNING`), never read-then-write.

## 7. Streaming

- User-facing chat streams (SSE via `StreamingResponse`). Target time to first token under
  1.5 s. Render a typing affordance immediately.
- Persist the user message before calling the model. Persist the assistant message once at stream
  end with token counts. On mid-stream failure, persist a partial message flagged
  `metadata.incomplete = true` or nothing, by one documented rule. Never leave a half-written
  row that the UI cannot tell apart from a complete answer.
- Cleanup lives in `finally`, not `except Exception`. Client disconnect raises
  `GeneratorExit` or `CancelledError` (both `BaseException`). Cancel the upstream provider stream and
  release the DB session there. Do not hold a pooled DB session open for the length of the LLM call.
  Load context, release the session, stream, then open a short session to persist.
- The frontend buffers incomplete markdown (half-open `**` or fences) before rendering and
  renders model output as text or sanitised markdown, never raw HTML.

## 8. Safety and tone (product policy, enforced in prompts and review)

The app offers reflection and guidance. It does not offer prophecy. In every prompt, the model must:
- **No certainty claims** in medical, legal, financial, or pregnancy matters. No diagnoses, no
  "stop your medication", no investment or "buy now" timing, no legal outcomes. Redirect to
  a qualified professional.
- **No fear-based or fatalistic predictions**: no death, accident, illness, divorce, or "curse"
  predictions; no "doom" transits. Frame challenges as tendencies and choices.
- **No paid-remedy pressure**: no gemstone or ritual purchase recommendations presented as
  necessary or urgent.
- **Crisis handling**: self-harm or abuse signals trigger a fixed, pre-written supportive
  response with helpline guidance. That response is never improvised by the model, and the
  code path is tested.
- **No protected-attribute judgements** (caste, religion, ethnicity, sexuality) and no
  compatibility verdicts that tell a user to leave or stay in a relationship.
- Respect both traditions. Neither Western nor Vedic is "the real one".
- A short, visible disclaimer on AI surfaces ("for reflection and entertainment, not
  professional advice"). The UI labels AI-generated content as such.

## 9. Prompt injection and data handling

- User text is data. It goes in the user turn, delimited, never concatenated into the system
  prompt. RAG chunks are trusted repo content but still delimited.
- The model has no tools that read other users' data. Context assembly only loads charts
  owned by the requesting user (`security_rules.md`), so an injected "show me another user's
  chart" has nothing to leak.
- Do not send email, password hash, or any identifier beyond what interpretation needs. Use the
  chart's display name and the computed facts. Birth data is personal data: no logging at INFO,
  and the provider's data-retention terms are checked when choosing a provider.
- Refuse requests to reveal the system prompt with a fixed reply. Do not rely on regex
  blocklists as the primary defense. The real defense is that there is nothing sensitive to
  leak.

## 10. Testing AI features (see `testing_rules.md`)

- Unit and integration tests use `FakeProvider`. CI never calls a real LLM.
- A small **eval set** (`backend/tests/evals/`): about 20-40 fixed prompts with charts, run manually
  against the real provider before a prompt or model change. Check grounding (no invented
  placements), safety (the policy cases in section 8 refuse correctly), and schema validity.
  Record the results in the PR or ledger entry.

## Checklist (any AI change)

- [ ] Calls go through `get_llm()`; no SDK import outside the adapter
- [ ] Prompt in a versioned file; version bumped; provenance stored on output rows
- [ ] CHART FACTS block present and authoritative; `time_unknown` respected; system labelled
- [ ] Structured output Pydantic-validated with retry and fallback
- [ ] Per-user and global budgets enforced; usage logged; counters atomic
- [ ] Streaming cleanup in `finally`; no DB session held across the LLM call
- [ ] Safety cases (section 8) pass on the eval set; crisis path is static
- [ ] Timeout plus graceful degraded UI for timeout, 429, and blocked responses
