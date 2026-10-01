"""Header-based markdown chunking (llm-integration.md §6.2).

- Split on H2/H3. Target 300-500 tokens; adjacent small H3 sections under the same H2 are
  merged up to the target; oversize sections split at paragraph boundaries with a 60-token
  overlap.
- Each chunk is prefixed with its heading path ("Planets > Saturn > Transit Effects").
- IDs are stable: "{file_stem}#{heading_slug}#{n}". Content hash drives re-indexing.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.llm.lexicon import detect_entities, detect_topics
from app.rag.frontmatter import split_front_matter
from app.rag.sources import SourceInfo, source_info

TARGET_MIN = 300
TARGET_MAX = 500
OVERLAP = 60
_TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def count_tokens(text: str) -> int:
    """Word-piece-ish estimate; close to BPE counts for English prose (within ~15 %)."""
    return len(_TOKEN.findall(text))


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60] or "section"


@dataclass(frozen=True)
class Chunk:
    id: str
    file: str
    heading_path: str
    system: str
    content: str                    # heading path line + body; this is what gets embedded
    topics: tuple[str, ...] = ()
    entities: tuple[str, ...] = ()
    content_sha256: str = field(default="")
    tokens: int = 0
    meta: dict = field(default_factory=dict)   # source_title, tradition, tier, licence, language, quality
    quality: float = 1.0


@dataclass
class _Section:
    h2: str
    h3: str | None
    body: list[str]

    @property
    def text(self) -> str:
        return "\n".join(self.body).strip()


def _sections(md: str) -> list[_Section]:
    secs: list[_Section] = []
    h2, h3 = "Overview", None
    cur = _Section(h2, h3, [])
    in_fence = False
    for line in md.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
        m = None if in_fence else _HEADING.match(line)
        if m and len(m.group(1)) in (1, 2, 3):
            level, title = len(m.group(1)), m.group(2).strip()
            if cur.text:
                secs.append(cur)
            if level == 1:
                h2, h3 = "Overview", None
            elif level == 2:
                h2, h3 = title, None
            else:
                h3 = title
            cur = _Section(h2, h3, [])
            continue
        cur.body.append(line)
    if cur.text:
        secs.append(cur)
    return secs


TABLE_MAX = 340          # tables larger than this are split row-group-wise (header repeated)
_TABLE_SEP = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
_DEGREE_TABLE = re.compile(r"(?:Exaltation|Fall|Debilitation)[^\n]{0,40}\(\d{1,2}\s?°\)", re.I)


def _is_table(p: str) -> bool:
    lines = p.splitlines()
    return len(lines) >= 3 and all(l.lstrip().startswith("|") for l in lines) and bool(_TABLE_SEP.match(lines[1]))


def _first_cell(row: str) -> str:
    cell = row.strip().strip("|").split("|")[0]
    return re.sub(r"[*_`]", "", cell).strip()


def _split_table(p: str, max_tokens: int) -> list[tuple[str, str | None]]:
    """Row groups of one markdown table, header + separator repeated on every group. The label names the first
    and last row so the heading path (full-text weight A) carries the rows' identity."""
    lines = p.splitlines()
    header, rows = lines[:2], lines[2:]
    groups: list[list[str]] = []
    cur: list[str] = []
    for r in rows:
        if cur and count_tokens("\n".join(header + cur + [r])) > max_tokens:
            groups.append(cur)
            cur = []
        cur.append(r)
    if cur:
        groups.append(cur)
    out = []
    for g in groups:
        first, last = _first_cell(g[0]), _first_cell(g[-1])
        label = f"rows {first} to {last}" if first and last and first != last else (f"row {first}" if first else None)
        out.append(("\n".join(header + g), label))
    return out


def _split_paragraphs(text: str, max_tokens: int, overlap: int) -> list[tuple[str, str | None]]:
    """-> [(part text, optional row-group label)]. Tables are never cut mid-row: a table over TABLE_MAX is split
    into row groups with its header repeated; a table of Western dignity degrees always stands alone."""
    text = re.sub(r"(?m)^(#{2,6} .*)\n(?!\n)", r"\1\n\n", text)      # a heading line never glues onto the table below it
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    parts: list[tuple[str, str | None]] = []
    cur: list[str] = []

    def flush() -> None:
        if cur:
            parts.append(("\n\n".join(cur), None))
            cur.clear()

    for p in paras:
        if _is_table(p) and (_DEGREE_TABLE.search(p) or count_tokens(p) > TABLE_MAX):
            flush()
            if _DEGREE_TABLE.search(p):
                parts.append((p, "dignity degrees"))
            else:
                parts.extend(_split_table(p, TABLE_MAX))
            continue
        pieces = p.splitlines() if count_tokens(p) > max_tokens else [p]
        for piece in pieces:
            if cur and count_tokens("\n\n".join(cur + [piece])) > max_tokens:
                joined = "\n\n".join(cur)
                parts.append((joined, None))
                tail = _tail(joined, overlap)
                cur[:] = [tail] if tail else []
            cur.append(piece)
    flush()
    return parts


def _tail(text: str, tokens: int) -> str:
    words = text.split()
    acc: list[str] = []
    for w in reversed(words):
        acc.insert(0, w)
        if count_tokens(" ".join(acc)) >= tokens:
            break
    return " ".join(acc)


_ALPHA = re.compile(r"[A-Za-z\u0900-\u097F]")


def quality_score(body: str, tokens: int) -> float:
    """0..1 heuristic: penalise stubs, table/symbol soup and repeated lines. Used to drop junk chunks
    and exposed in meta so retrieval can down-weight weak ones."""
    if tokens <= 0:
        return 0.0
    letters = len(_ALPHA.findall(body)) / max(1, len(body))
    lines = [l.strip() for l in body.splitlines() if l.strip()]
    uniq = len(set(lines)) / max(1, len(lines))
    size = min(1.0, tokens / 80.0)
    body_q = 0.6 * min(1.0, letters / 0.6) + 0.4 * uniq
    return round(max(0.0, min(1.0, body_q * (0.3 + 0.7 * size))), 3)


_DIFFER = re.compile(r"\b(?:differ(?:s|ent|ence)?|vary|varies|varying|disagree\w*|some (?:schools|sources|traditions|texts|astrologers)|other (?:schools|sources|traditions)|"
                     r"one (?:school|tradition|source)|alternative|variant|depending on the (?:school|source|tradition)|according to (?:some|one))\b", re.I)
_DEV = re.compile(r"[\u0900-\u097F]")


def chunk_markdown(md: str, file_name: str, *, system: str | None = None, info: SourceInfo | None = None,
                   min_quality: float = 0.25) -> list[Chunk]:
    stem = Path(file_name).stem
    front, md = split_front_matter(md, stem)           # the YAML block is metadata, never chunk text
    info = info or source_info(stem, front)
    doc_title = info.title if front else stem.replace("_", " ").title()
    sys_tag = system or info.system
    # 1. merge adjacent small sections that share an H2 (at most info.max_merge entries per chunk when set)
    groups: list[tuple[str, str | None, str, int]] = []
    for s in _sections(md):
        label = s.h3
        if groups and groups[-1][0] == s.h2 and count_tokens(groups[-1][2]) < TARGET_MIN \
                and count_tokens(groups[-1][2] + s.text) <= TARGET_MAX \
                and not (info.max_merge and groups[-1][3] >= info.max_merge):
            g = groups[-1]
            merged_label = g[1] if g[1] and not label else (f"{g[1]} / {label}" if g[1] and label else label or g[1])
            heading_line = f"### {label}\n" if label else ""
            groups[-1] = (g[0], merged_label, f"{g[2]}\n\n{heading_line}{s.text}", g[3] + 1)
        else:
            groups.append((s.h2, label, s.text, 1))
    # 2. split oversize / tables, build chunks
    chunks: list[Chunk] = []
    counters: dict[str, int] = {}
    for h2, h3, body, _n in groups:
        base_path = " > ".join(p for p in (doc_title, h2, h3) if p)
        if info.exclude(base_path):
            continue
        for part, label in _split_paragraphs(body, TARGET_MAX, OVERLAP):
            if label == "dignity degrees":
                path = " > ".join((doc_title, h2, "Dignity table (Western tropical degrees)"))
            else:
                path = f"{base_path} > {label}" if label else base_path
            content = f"{path}\n\n{part}"
            q = quality_score(part, count_tokens(part))
            if q < min_quality:
                continue
            key = slug(f"{h2}-{h3}" if h3 else h2)
            n = counters.get(key, 0)
            counters[key] = n + 1
            western_degrees = bool(_DEGREE_TABLE.search(part)) and info.system in ("both", "western")
            lang = "hi" if len(_DEV.findall(part)) > 0.25 * max(1, len(part.split())) else info.language
            meta = {**info.meta(), "quality": q, "language": lang,
                    "kind": "table" if _is_table(part) or part.count("\n|") >= 3 else "prose"}
            if meta.get("schools_differ") and not _DIFFER.search(part):
                meta["schools_differ"] = False                 # file-level school_notes only apply where the chunk says so
                meta.pop("school_note", None)
            if "[unverified]" in part.lower():
                meta["unverified"] = True
            if western_degrees:
                meta["degree_system"] = "western"     # Western exaltation degrees differ from the Vedic set
            chunks.append(Chunk(
                id=f"{stem}#{key}#{n}", file=f"{stem}.md", heading_path=path,
                system="western" if western_degrees else sys_tag, content=content,
                topics=tuple(detect_topics(content)), entities=tuple(detect_entities(content)),
                content_sha256=hashlib.sha256(content.encode()).hexdigest(), tokens=count_tokens(content),
                meta=meta, quality=q,
            ))
    return chunks


def chunk_corpus(kb_dir: Path) -> list[Chunk]:
    out: list[Chunk] = []
    for path in sorted(kb_dir.glob("*.md")):
        if path.name.startswith("_"):
            continue
        out.extend(chunk_markdown(path.read_text(encoding="utf-8"), path.name))
    out = dedupe(out)
    ids = [c.id for c in out]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate chunk ids")
    return out


def _shingles(text: str, n: int = 5) -> set[int]:
    w = re.findall(r"\w+", text.lower())
    return {hash(tuple(w[i:i + n])) for i in range(max(0, len(w) - n + 1))}


def near_duplicates(chunks: list[Chunk], threshold: float = 0.85) -> list[tuple[str, str, float]]:
    """Pairs of chunks whose 5-word shingle Jaccard similarity is >= threshold."""
    sh = [(_shingles(c.content.split("\n\n", 1)[-1]), c) for c in chunks]
    pairs = []
    for i in range(len(sh)):
        for j in range(i + 1, len(sh)):
            a, b = sh[i][0], sh[j][0]
            if not a or not b:
                continue
            inter = len(a & b)
            if inter and inter / len(a | b) >= threshold:
                pairs.append((sh[i][1].id, sh[j][1].id, round(inter / len(a | b), 3)))
    return pairs


def dedupe(chunks: list[Chunk], threshold: float = 0.85) -> list[Chunk]:
    """Drop the lower-authority (higher tier number, then lower quality) member of each near-duplicate pair."""
    by_id = {c.id: c for c in chunks}
    drop: set[str] = set()
    for a, b, _ in near_duplicates(chunks, threshold):
        ca, cb = by_id[a], by_id[b]
        loser = max((ca, cb), key=lambda c: (c.meta.get("tier", 1), -c.quality))
        drop.add(loser.id)
    return [c for c in chunks if c.id not in drop]
