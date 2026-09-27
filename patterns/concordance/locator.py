#!/usr/bin/env python3
"""Reference implementation: locate each chapter of a compiled book in its built PDF.

This is the portable core of the pattern, extracted from a working build. It is
NOT a drop-in: two functions are stubs you must implement against your own
manifest format, and they are marked TODO. Everything else works as written.

What is portable (do not rewrite these — they encode the hard-won bits):
  norm / needles   prose fingerprinting that survives a PDF text layer
  find_page        forward scan from a monotonic cursor
  page_ranges      chapter extent derived from the next located chapter
  emit             the JSON contract the page consumes

What is yours:
  walk_book        resolve your manifest to ordered (title, body, sources) entries
  sources_of       map your manifest's provenance fields to the three roles

Requires: pypdf
Usage:
  ./locator.py --pdf build/Book.pdf --book Book --edition complete > xref.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

FENCE_BLOCK_RE = re.compile(r"```.*?```", re.S)
HTML_RE = re.compile(r"<[^>]+>")
FIGURE_RE = re.compile(r"^\s*(?:!\[|\|)")

ROLES = ("sliced", "adapted", "authored")


def norm(text: str) -> str:
    """Collapse to comparable characters.

    Dropping everything but alphanumerics is what makes a needle survive the PDF
    text layer: hyphenation, ligatures, smart quotes and soft line breaks all
    disappear on both sides of the comparison.
    """
    return re.sub(r"[^a-z0-9]", "", text.lower())


def needles(body: str, count: int = 4, size: int = 45) -> list[str]:
    """Prose fingerprints for one chapter.

    Never fingerprint the title: in any book with a table of contents the TOC
    entry matches first and every chapter reports page 3. Headings, code fences,
    figures and table rows are skipped because they reflow or repeat.

    Four needles of 45 characters is enough to be unique in a 500-page book and
    short enough to survive a mid-needle line break. Longer is more fragile.
    """
    body = FENCE_BLOCK_RE.sub(" ", body)
    body = HTML_RE.sub(" ", body)
    out = []
    for line in body.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or FIGURE_RE.match(line):
            continue
        n = norm(line)
        if len(n) >= size:
            out.append(n[:size])
        if len(out) >= count:
            break
    return out


def page_texts(pdf: Path) -> list[str]:
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit("pypdf not found — pip install pypdf")
    return [norm(p.extract_text() or "") for p in PdfReader(str(pdf)).pages]


def find_page(pages: list[str], probes: list[str], start: int) -> int | None:
    """First page at or after `start` containing any probe. 1-based.

    The cursor only moves forward, which is correct because chapters appear in
    manifest order, and it stops a late chapter matching a stray earlier quote.
    """
    for i in range(start, len(pages)):
        if any(p in pages[i] for p in probes):
            return i + 1
    return None


def page_ranges(rows: list[dict], total: int) -> None:
    """Fill each row's `pages` from its own start and the next located start.

    A chapter runs up to wherever the next one begins; the last runs to the end.
    Rows that never located get "?" and are dropped from the page-map strip.
    """
    for i, r in enumerate(rows):
        nxt = next((rows[j]["page"] for j in range(i + 1, len(rows)) if rows[j]["page"]), None)
        if r["page"] and nxt and nxt > r["page"]:
            r["pages"] = f"{r['page']}–{nxt - 1}" if nxt - 1 > r["page"] else str(r["page"])
        elif r["page"]:
            r["pages"] = f"{r['page']}–{total}" if i == len(rows) - 1 else str(r["page"])
        else:
            r["pages"] = "?"


def sources_of(entry: dict) -> list[dict]:
    """TODO — map your manifest's provenance fields onto the three roles.

    The shape below matches a manifest where `file` is an authored chapter,
    `source` + `from`/`to` slices a span out of a canon file, and `derived_from`
    declares what a hand-rewritten chapter was adapted from. Rewrite the field
    names; keep the three roles and keep returning one entry per anchor.
    """
    out = []
    if "file" in entry:
        out.append({"role": "authored", "path": entry["file"], "anchor": ""})
    if "source" in entry:
        span = " → ".join(x for x in (entry.get("from"), entry.get("to")) if x)
        out.append({"role": "sliced", "path": entry["source"], "anchor": span})
    for d in entry.get("derived_from", []):
        for anchor in d.get("anchors", [""]) or [""]:
            out.append({"role": "adapted", "path": d["file"], "anchor": anchor})
    if not out:
        raise ValueError(f"entry has no source: {entry.get('title') or entry}")
    return out


def walk_book(manifest: Path, edition: str) -> list[dict]:
    """TODO — resolve your manifest to ordered entries, in built order.

    Each entry needs: part, kind, title, words, figures, sources, and the
    resolved markdown `body` (used only to fingerprint, then discarded).

    The one rule that matters here: **call your own builder's resolver**. Import
    the build script and reuse the function that produces chapter text, rather
    than re-reading the manifest yourself. Two resolvers drift, and then the
    concordance describes a book you never built.
    """
    raise NotImplementedError(
        "implement walk_book() against your manifest — see the module docstring")


def emit(rows: list[dict], pdf: Path, book: str, edition: str, generated: str) -> dict:
    return {
        "generated": generated,
        "totals": {pdf.name: len(page_texts(pdf))},
        "rows": [{"book": book, "edition": edition, "pdf": pdf.name,
                  "part": r["part"], "kind": r.get("kind", "chapter"), "title": r["title"],
                  "words": r["words"], "figures": r.get("figures", ""),
                  "pages": r["pages"], "sources": r["sources"]}
                 for r in rows],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--book", required=True)
    ap.add_argument("--edition", default="complete")
    ap.add_argument("--generated", default="", help="build date; defaults to the PDF's mtime")
    args = ap.parse_args()

    import datetime as dt
    generated = args.generated or dt.date.fromtimestamp(args.pdf.stat().st_mtime).isoformat()

    pages = page_texts(args.pdf)
    rows = walk_book(args.manifest, args.edition)

    cursor = 0
    for r in rows:
        r["page"] = find_page(pages, needles(r["body"]), cursor)
        if r["page"]:
            cursor = r["page"] - 1
    page_ranges(rows, len(pages))

    missing = [r["title"] for r in rows if r["pages"] == "?"]
    json.dump(emit(rows, args.pdf, args.book, args.edition, generated),
              sys.stdout, ensure_ascii=False, indent=1)
    if missing:
        # Not cosmetic: an unlocated chapter leaves the cursor parked, so the NEXT
        # chapter can match too early and swallow a large span of pages.
        print(f"\nwarning: {len(missing)} entries could not be located: "
              f"{', '.join(missing)}", file=sys.stderr)


if __name__ == "__main__":
    main()
