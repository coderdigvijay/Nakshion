#!/usr/bin/env python3
"""Fail if the inline <script> hash(es) in frontend/dist/index.html are not allowed by the CSP in frontend/vercel.json.
Run after `npm run build`. (An unlisted inline script is blocked by the browser: the app would render blank.)"""
import base64
import hashlib
import json
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "frontend"
html = (root / "dist" / "index.html").read_text(encoding="utf-8")
csp = next(
    h["value"]
    for block in json.loads((root / "vercel.json").read_text())["headers"]
    for h in block["headers"]
    if h["key"] == "Content-Security-Policy"
)
bad = 0
for m in re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S):
    digest = "sha256-" + base64.b64encode(hashlib.sha256(m.group(1).encode()).digest()).decode()
    if f"'{digest}'" in csp:
        print(f"ok: inline script {digest[:16]}... is allowed by the CSP")
    else:
        print(f"MISSING: add '{digest}' to script-src in frontend/vercel.json", file=sys.stderr)
        bad += 1
sys.exit(1 if bad else 0)
