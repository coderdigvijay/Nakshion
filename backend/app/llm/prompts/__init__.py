"""Versioned prompt templates with provenance (ai_llm_rules §2, llm-integration.md §9.4).

Layout: prompts/<task>/v<N>.j2, shared partials in prompts/_partials/, and registry.yaml
mapping each task to its active version plus a sha256 lock of every released file.

A released file is immutable: editing one in place changes its hash and `PromptRegistry.verify()`
(run in tests and at startup) fails. Change a prompt by adding v<N+1> and bumping `active`.
Regenerate locks for NEW files only with: python -m app.llm.prompts --lock
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from jinja2 import FileSystemLoader, StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

PROMPTS_DIR = Path(__file__).parent
REGISTRY = PROMPTS_DIR / "registry.yaml"


@dataclass(frozen=True)
class RenderedPrompt:
    prompt_id: str      # "chat@v1"
    text: str
    sha256: str         # of the rendered template source(s), for provenance


class PromptRegistry:
    def __init__(self, root: Path = PROMPTS_DIR) -> None:
        self.root = root
        self.reg = yaml.safe_load((root / "registry.yaml").read_text(encoding="utf-8"))
        # Sandboxed + StrictUndefined: only code-supplied variables, never user text, are rendered.
        self.env = SandboxedEnvironment(
            loader=FileSystemLoader(str(root)), undefined=StrictUndefined, autoescape=False,
            keep_trailing_newline=False, trim_blocks=True, lstrip_blocks=True,
        )

    def active_version(self, task: str) -> str:
        return self.reg["active"][task]

    def render(self, task: str, version: str | None = None, **vars) -> RenderedPrompt:
        v = version or self.active_version(task)
        rel = f"{task}/{v}.j2"
        text = self.env.get_template(rel).render(**vars).strip()
        return RenderedPrompt(prompt_id=f"{task}@{v}", text=text,
                              sha256=hashlib.sha256(text.encode()).hexdigest()[:16])

    @staticmethod
    def file_hash(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def files(self) -> list[str]:
        return sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*.j2"))

    def verify(self) -> list[str]:
        """Problems: released files edited in place, files not locked, active versions missing."""
        problems = []
        locked: dict[str, str] = self.reg.get("released", {}) or {}
        for rel in self.files():
            h = self.file_hash(self.root / rel)
            if rel not in locked:
                problems.append(f"unlocked prompt file {rel} (run --lock after review)")
            elif locked[rel] != h:
                problems.append(f"released prompt {rel} was edited in place; add a new version instead")
        for task, v in (self.reg.get("active") or {}).items():
            if not (self.root / task / f"{v}.j2").exists():
                problems.append(f"active {task}@{v} does not exist")
        return problems


@lru_cache(maxsize=1)
def get_registry() -> PromptRegistry:
    return PromptRegistry()


LANGUAGE_INSTRUCTIONS = {
    "english": "English.",
    "hindi": "Hindi, written in Devanagari script. Astrological terms may stay in their usual form.",
    "hinglish": "Hinglish: conversational Hindi written in Roman (Latin) script, mixed naturally with English.",
}
