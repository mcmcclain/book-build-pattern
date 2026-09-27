#!/usr/bin/env python3
"""Smoke test for the portable half of locator.py — the part with no stubs."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "locator", Path(__file__).resolve().parents[1] / "locator.py")
loc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loc)

# norm() must erase exactly what a PDF text layer mangles.
assert loc.norm("Soft­hyphen — text") == "softhyphentext"
assert loc.norm("“Smart” quotes, ﬁ ligature") == "smartquotesﬁligature".replace("ﬁ", "")

# needles() must skip headings (they match the table of contents first),
# figures and table rows, and must truncate to `size`.
body = ("# Chapter 3 — Reading a Season\n"
        "![season wheel](fig.png)\n"
        "| a | b |\n"
        "Short line.\n"
        "The frost date is not a promise; it is the midpoint of a distribution.\n")
n = loc.needles(body, count=4, size=45)
assert n, "no needles produced"
assert all(len(x) == 45 for x in n), [len(x) for x in n]
assert not any("chapter3" in x for x in n), "heading leaked into a needle"
assert not any("seasonwheel" in x for x in n), "figure leaked into a needle"

# find_page() scans forward only, from a monotonic cursor.
pages = ["", "thefrostdateisnotapromise", "", "thefrostdateisnotapromise"]
assert loc.find_page(pages, ["thefrostdateisnotapromise"], 0) == 2
assert loc.find_page(pages, ["thefrostdateisnotapromise"], 2) == 4
assert loc.find_page(pages, ["absent"], 0) is None

# page_ranges(): extent comes from the next located chapter; last runs to the end;
# unlocated rows get "?" and are dropped from the strip.
rows = [{"page": 1}, {"page": 5}, {"page": None}, {"page": 9}]
loc.page_ranges(rows, 12)
assert [r["pages"] for r in rows] == ["1–4", "5–8", "?", "9–12"], [r["pages"] for r in rows]

# A single-page chapter must not render as "7–7".
rows = [{"page": 7}, {"page": 8}]
loc.page_ranges(rows, 8)
assert rows[0]["pages"] == "7", rows[0]["pages"]

# sources_of() yields one entry per adapted anchor, and refuses a sourceless entry.
got = loc.sources_of({"file": "book/ch.md", "derived_from": [
    {"file": "canon/A.md", "anchors": ["^## One", "^## Two"]}]})
assert [s["role"] for s in got] == ["authored", "adapted", "adapted"], got
try:
    loc.sources_of({"title": "orphan"})
except ValueError:
    pass
else:
    raise AssertionError("sourceless entry should raise")

print("locator core: all checks passed")
