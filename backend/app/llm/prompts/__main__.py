"""python -m app.llm.prompts [--lock]  : verify (default) or lock NEW prompt files.

--lock only adds hashes for files that are not yet locked; it never rewrites an existing
lock, so it cannot be used to bless an in-place edit of a released prompt.
"""

from __future__ import annotations

import sys

import yaml

from app.llm.prompts import REGISTRY, PromptRegistry


def main() -> int:
    reg = PromptRegistry()
    if "--lock" in sys.argv:
        data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
        released = data.setdefault("released", {}) or {}
        added = []
        for rel in reg.files():
            if rel not in released:
                released[rel] = reg.file_hash(reg.root / rel)
                added.append(rel)
        data["released"] = dict(sorted(released.items()))
        REGISTRY.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        print("locked:", ", ".join(added) or "(nothing new)")
    problems = PromptRegistry().verify()
    for p in problems:
        print("PROBLEM:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
