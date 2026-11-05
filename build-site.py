#!/usr/bin/env python3
"""Wraps index.html (Artifact format, no document tags) into docs/index.html for GitHub Pages
and copies the game art next to it."""
import shutil
from pathlib import Path

root = Path(__file__).parent
docs = root / "docs"
docs.mkdir(exist_ok=True)
page = (root / "index.html").read_text(encoding="utf-8")
cut = page.index('<div class="rotate"')
head, body = page[:cut], page[cut:]
extra = """<meta name="description" content="Samuel Pepys steps out of his portrait and tells children the story of the Great Fire of London, 1666.">
<meta name="theme-color" content="#141a2b">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<style>:root { padding-top: env(safe-area-inset-top, 0px); padding-bottom: env(safe-area-inset-bottom, 0px); }</style>
"""
(docs / "index.html").write_text(
    '<!doctype html>\n<html lang="en">\n<head>\n' + head + extra + "</head>\n<body>\n" + body + "</body>\n</html>\n",
    encoding="utf-8",
)
if (docs / "art").exists():
    shutil.rmtree(docs / "art")
shutil.copytree(root / "art", docs / "art", ignore=shutil.ignore_patterns("*.json"))
(docs / ".nojekyll").write_text("")
print("docs/ ready")
