# Concordance

**A source ↔ chapter ↔ page cross-reference for books compiled from files.**

[**See the live example →**](https://mcmcclain.github.io/book-build-pattern/patterns/concordance/example/)
· built from [`example/fixture.json`](example/fixture.json) by
[`example/build-example.py`](example/build-example.py)

The thing you are building answers two questions about a book that is assembled from files
rather than typed into one document:

- **Forward** — what is this chapter made of?
- **Reverse** — if I edit this file, what breaks?

The second question is the one that justifies the work. In a repo where chapters are sliced
out of source documents at build time, a one-line edit to a source file can move six chapters
across three books, and nothing in the repo tells you that.

The output is a **single self-contained HTML file committed to the repo**. It has no server,
no build step at view time, and no runtime dependency — it opens from `file://`, from a Pages
deploy, or from an attachment, and it will still open in five years.

---

## 0. What to copy

| File | Goes to | Role |
|---|---|---|
| `xref-page.template.html` | wherever your book docs live | the page, minus data and project strings |
| `locator.py` | `scripts/` | reference implementation — two functions are stubs you implement |
| `example/build-example.py` | `scripts/` | the fill step; works unchanged against your own payload |
| `guardrails.instructions.md` | `.github/instructions/` | **the guardrails** — path-scoped, loads only on the paths that matter |
| `concordance.prompt.md` | `.github/prompts/` | the runbook — invoke as `/concordance` |

Read this document once, when building the thing. Then don't: the rules that must hold *every*
time live in **[`guardrails.instructions.md`](guardrails.instructions.md)**, which is short on
purpose. A guardrail buried inside 500 lines of design rationale is a guardrail nobody loads.

This README is the *why*. The instructions file is the *always*. The prompt file is the
*how, today*.

### If an agent is doing the work

The instructions file is written for GitHub Copilot's path-scoped format
(`.github/instructions/*.instructions.md`, `applyTo:` globs) and the prompt file for its
on-demand format (`.github/prompts/*.prompt.md`, invoked as `/concordance`). Both are plain
Markdown with frontmatter, so they port to any agent that reads repo instructions — adjust the
frontmatter keys and the globs.

**One rule matters more than the rest, and it is the one that gets violated.** Asked for a page
like this, a coding agent will reach for generating fresh HTML, and you get a plausible
table-based approximation that has lost the scaled page-map strips, the filter
cross-highlighting, the theme handling and the keyboard affordances. The template is 22KB of
already-debugged design: an input to be filled, never a reference to be imitated. Fill it with
a script. If you enforce one thing from this whole repo, enforce that.

---

## 1. Preconditions

Do not start until all four are true. Without them the page has nothing to render and you
will end up hand-maintaining a table, which is worse than no table.

| # | Precondition | Why |
|---|---|---|
| 1 | The book is **declared**, not typed — a manifest lists chapters in order | The manifest is the only place provenance can live |
| 2 | Each manifest entry **names its source** | No source, no cross-reference |
| 3 | The build emits a **PDF you can read the text layer of** | Page numbers come from the built artifact, not from the manifest |
| 4 | The build is **reproducible** — same inputs, same PDF | Otherwise page numbers rot between the build and the page |

If your book is a single hand-written manuscript, stop. This pattern has nothing to offer
you. It is for compiled books.

---

## 2. Architecture — three seams

```
MANIFEST.json ──┐
                ├─► build-book.py   ─► BOOK.pdf
source files ───┘         │
                          │ (same resolver, imported)
                          ▼
                     locator.py    ─► rows[] as JSON
                          │              │
                    XREF.md / .csv       │  injected at {{XREF_JSON}}
                    (repo-readable)      ▼
                                  xref-page.template.html
                                          │
                                          ▼
                                    published page
```

Three properties matter more than any code below:

1. **The locator imports the builder.** `locator.py` must not re-implement manifest
   resolution — it loads `build-book.py` as a module and calls its `resolve_entry`. If it
   re-implemented it, the two would drift and the concordance would describe a book you
   never built. This is the single most important design decision in the whole recipe.

2. **The generator emits data, never HTML.** One `rows[]` array feeds a Markdown table, a
   CSV, and the page. Markdown is what lives in the repo and shows up in diffs; the page is
   for reading.

3. **The page is one file with the data inlined.** No fetch, no build step, no server. It
   opens from disk, from a published URL, or from an email attachment, and it will still
   open in five years.

---

## 3. The JSON contract

This is the only part you must copy exactly. Everything else is replaceable. One object per
placed chapter, flat, repeated per book *and* per edition.

```json
{
  "generated": "2026-03-14",
  "totals": { "Almanac_2026-03-14.pdf": 96 },
  "rows": [
    {
      "book":    "Almanac",
      "edition": "complete",
      "pdf":     "Almanac_2026-03-14.pdf",
      "part":    "Part II — The Year",
      "kind":    "chapter",
      "title":   "Chapter 3 — Reading a Season",
      "words":   3260,
      "figures": "season-wheel, frost-map",
      "pages":   "29–48",
      "sources": [
        { "role": "sliced", "path": "canon/SEASONS.md",
          "anchor": "^# Reading a Season → ^## The Long View" }
      ]
    }
  ]
}
```

| Field | Type | Notes |
|---|---|---|
| `generated` | date string | Rendered in the stamp line. Not parsed. |
| `totals` | `{pdf → page count}` | **Required** — the page-map strips are drawn to scale against it |
| `book` | string | Groups strips and short badges. Same value across editions of one book |
| `edition` | string | `book\|edition` is the strip identity |
| `pdf` | string | Must be a key in `totals` |
| `part` | string | Free text, shown as a column and in the hover caption |
| `kind` | string | `chapter` / `bridge` / `appendix` / `frontmatter` / `reference`. Display only |
| `title` | string | Chapter display name |
| `words` | int | Sanity signal — a 400-word chapter next to a 7,000-word one is usually a bug |
| `figures` | string | Comma-joined ids, `""` when none |
| `pages` | `"57"`, `"57–72"`, or `"?"` | **En dash.** `?` means the locator failed — the segment is dropped from the strip |
| `sources[]` | array | **Never empty.** Order matters only for display |
| `sources[].role` | enum | See below — drives every colour on the page |
| `sources[].path` | string | Repo-relative. The join key for the whole reverse view |
| `sources[].anchor` | string | The locator within the source, `""` when the whole file |

### The role enum is the heart of it

Three values, and they are a **provenance claim about how words got into the book**:

- **`sliced`** — cut out of a source file at build time by anchors. Edit the source and the
  next build carries the change. This is the only role with a mechanical guarantee.
- **`adapted`** — re-voiced by hand from a named source. No guarantee; the source moving is
  a *signal to re-read*, not an automatic update. This is what you use when tone conversion
  is authorship rather than a build transform.
- **`authored`** — written in the book folder, no upstream source.

Pick three words that fit your project if these do not, but **keep exactly three, and keep
the ordering semantics**: a chapter's strip colour is the most-coupled role present —
`sliced` beats `adapted` beats `authored`. That rule is four lines in the renderer:

```js
function role(r){
  var roles = r.sources.map(function(s){ return s.role; });
  return roles.indexOf("sliced")>-1 ? "sliced"
       : roles.indexOf("adapted")>-1 ? "adapted" : "authored";
}
```

If you add a fourth role you must also add a CSS token trio (`--x`, `--x-bg`) and a `.r-x`
chip class, in both themes.

---

## 4. Step one — make the manifest carry provenance

Entries need one of three shapes. These are the real shapes from this repo.

**Authored** — a file in the book folder:

```json
{ "kind": "chapter", "file": "chapters/ch06-grafting.md",
  "title": "Chapter 6 — Grafting", "editions": ["complete", "public"] }
```

**Sliced** — a span cut out of a source document by regex anchors:

```json
{ "title": "Chapter 1 — What Soil Is",
  "source": "canon/SOIL.md",
  "from": "^# What Soil Is",
  "to": "^## Amendments",
  "transforms": ["unwrap", "promote_headings"],
  "prepend_title": true,
  "editions": ["complete", "public"] }
```

**Adapted** — authored prose that declares what it was re-voiced from:

```json
{ "file": "chapters/pg-01-not-a-plan.md",
  "title": "You Are Not Growing a Plan",
  "editions": ["public"],
  "derived_from": [
    { "file": "canon/SEASONS.md",
      "anchors": ["^## Why the calendar lies", "^## Reading the week ahead"] }
  ] }
```

`derived_from` is the piece people skip, and it is the piece that pays. It is a hand-authored
chapter *declaring its upstream*, which turns an untrackable rewrite into a testable one.
Back it with a test that fails when an anchor stops resolving. The test does not verify
meaning — it guarantees that drift is **loud instead of silent**, and forces a human re-read of
the adaptation when the source moves.

Then the extraction is one function:

```python
def sources_of(entry: dict) -> list[tuple[str, str, str]]:
    out = []
    if "file" in entry:
        out.append(("authored", entry["file"], ""))
    if "source" in entry:
        span = " → ".join(x for x in (entry.get("from"), entry.get("to")) if x)
        out.append(("sliced", entry["source"], span))
    for d in entry.get("derived_from", []):
        for anchor in d.get("anchors", [""]) or [""]:
            out.append(("adapted", d["file"], anchor))
    return out
```

Note that `file` and `source` are not exclusive in principle, and an adapted chapter yields
both an `authored` row and one `adapted` row per anchor. That is intentional: the reverse
view should list a source once per anchor that touches it.

---

## 5. Step two — locate each chapter in the built PDF

The manifest gives you order. It cannot give you pages; only the rendered PDF knows those.

### Match prose, not titles

The naive approach — search the PDF for the chapter title — fails on any book with a table
of contents, because the TOC match comes first and every chapter reports page 3. Instead,
fingerprint the chapter's **body prose**:

```python
def norm(text):                       # collapse to comparable characters
    return re.sub(r"[^a-z0-9]", "", text.lower())

def needles(body, count=4, size=45):
    body = FENCE_BLOCK_RE.sub(" ", body)   # code fences reflow unpredictably
    body = HTML_RE.sub(" ", body)
    out = []
    for line in body.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or FIGURE_RE.match(line):
            continue                       # headings hit the TOC; figures/tables reflow
        n = norm(line)
        if len(n) >= size:
            out.append(n[:size])
        if len(out) >= count:
            break
    return out
```

Stripping all non-alphanumerics is what makes this survive the PDF text layer: hyphenation,
ligatures, soft line breaks and smart quotes all disappear on both sides of the comparison.
Four needles of 45 characters is enough to be unique in a 560-page book and short enough to
survive a mid-needle line break — a longer needle is *more* fragile, not less.

### Scan forward from a monotonic cursor

```python
def find_page(pages, probes, start):
    for i in range(start, len(pages)):
        if any(p in pages[i] for p in probes):
            return i + 1
    return None
```

The cursor only advances, which is correct — chapters appear in manifest order — and it
stops a late chapter from matching a stray quotation earlier in the book.

**Known failure mode, and be honest about it in your footer:** when one chapter fails to
locate, the cursor does not advance, and the *next* chapter can match too early and swallow
a large span. It looks like one chapter reporting a single page while its neighbour reports a
forty-page range — plausible enough to survive review, and wrong. The `?` count printed to
stderr is your detector:

```
warning: 3 entries could not be located in their PDF
```

Treat a non-zero warning as a build failure to investigate, not a cosmetic note. The usual
cause is a chapter whose first 45-character prose line is a figure caption or a table row.

### Derive ranges from the next located chapter

A chapter's extent is "up to wherever the next one starts," with the last one running to the
end of the book:

```python
for i, r in enumerate(rows):
    nxt = next((rows[j]["page"] for j in range(i+1, len(rows)) if rows[j]["page"]), None)
    if r["page"] and nxt and nxt > r["page"]:
        r["pages"] = f"{r['page']}–{nxt-1}" if nxt-1 > r["page"] else str(r["page"])
    elif r["page"]:
        r["pages"] = f"{r['page']}–{len(pages)}" if i == len(rows)-1 else str(r["page"])
    else:
        r["pages"] = "?"
```

### Say what a page number means

`pages` is the **1-based PDF page index**, not the printed folio. Any book with roman front
matter and an arabic count restarting at the body will have a printed folio that runs behind
the index by the length of the front matter. Put that sentence in the page footer. Someone
will otherwise file a bug.

### Titles for entries the manifest does not name

Bridge entries in this repo carry no manifest title, and their heading `shift` pushes the
source heading past the window the builder's fallback looks at, so it returns a diagnostic
string instead of a name. Recover it from the resolved body:

```python
if not entry.get("title"):
    m = re.search(r"^#{1,6}\s+(.+)$", body, re.M)
    title = m.group(1).strip() if m else f"({entry.get('kind', 'untitled')})"
```

### Emit three formats from one pass

- `--format md` → commit it. This is what makes provenance reviewable in a pull request.
- `--format csv` → for spreadsheets and ad-hoc queries.
- `--format json` → feeds the page.

---

## 6. Step three — the page

Use `xref-page.template.html`, alongside this file. It is the finished concordance with the
payload and the project strings lifted out. **Fill it; do not rewrite it** —
[`guardrails.instructions.md`](guardrails.instructions.md) has the rule and the reason.

Placeholders, all required:

| Placeholder | Fill with |
|---|---|
| `{{PROJECT}}` `{{H1}}` `{{EYEBROW}}` `{{DECK}}` | Masthead text. `{{H1}}` is a short noun phrase |
| `{{ROLE_*_GLOSS}}` | One clause each defining your three roles |
| `{{BUILD_NOTE}}` | Which build this is and what changed in it |
| `{{PROVENANCE_NOTE}}` `{{REGEN_COMMAND}}` | Footer: what generated it, how to regenerate |
| `{{BOOK_LABELS}}` | JS object literal, `"book\|edition"` → display label |
| `{{BOOK_SHORT}}` | JS object literal, `book` → 2–3 char badge |
| `{{XREF_JSON}}` | The array from `--format json` |

`{{BOOK_LABELS}}` and `{{BOOK_SHORT}}` are **object literals, not strings** — no quotes
around the braces.

### What the page contains, in reading order

1. **Stamp + stat row** — builds, chapters placed, source files, sources shared by 2+ books.
   All four derived in the renderer; never passed in. The fourth is the one that earns its
   place: it is the count of files that can break more than one book.

2. **Page maps** — one horizontal strip per `book|edition`, drawn to scale across the real
   page count. Each segment is a chapter, width proportional to pages occupied, coloured by
   role. This is the element people react to, and it is cheap:

   ```js
   var pct = (s.len / total * 100).toFixed(3);
   // flex-basis, not width — segments tile a flex row exactly
   '<button class="seg" data-role="…" style="flex:0 0 '+pct+'%">'
   ```

   Segments are `<button>` elements, so they are tab-reachable and carry an `aria-label`.
   Hover *and* `focusin` both write the caption. A caption region with `min-height:2.9em`
   and an idle message stops the page jumping as you sweep across.

3. **Blast radius** — sources ranked by chapters reached, with a bar and a badge per book.
   Count a chapter **once per book**, not once per edition, or a two-edition book doubles
   every number. Clicking a row writes its path into the filter and scrolls to the controls:

   ```js
   var chs = {};
   index[p].forEach(function(h){ chs[h.row.book + "|" + h.row.title] = 1; });
   ```

4. **The cross-reference, both directions** — tabs for "By source" and "By chapter" over one
   shared filter. The filter searches a precomputed haystack per row (title, part, book,
   edition, every source path and anchor, lowercased) and **cross-highlights**: matching
   segments in the strips above stay at full opacity while the rest drop to `.16`. That link
   between the overview and the detail is most of the page's value.

Tab choice and filter text persist in `localStorage`, every access wrapped:

```js
function load(k){ try{ return localStorage.getItem(k); }catch(err){ return null; } }
```

Not optional — a private window or blocked site data makes the accessor *throw*, and an
unwrapped read takes the whole page down.

### Constraints worth knowing before you touch the CSS

- **Theme**: the palette is defined three times on purpose — the complete set of tokens on
  bare `:root`, redefined under `@media (prefers-color-scheme:dark)` guarded as
  `:root:not([data-theme="light"])`, and again under `:root[data-theme="dark"]` so an explicit
  toggle wins in both directions. `body` gets an explicit background token rather than
  inheriting. Keep that structure if you change the colours; a token defined only inside a
  media block breaks the toggle.
- **The data is inlined, not fetched, and that is the point.** A `fetch()` of a sibling JSON
  file fails outright under `file://` on Chrome and Safari — same-origin rules treat local
  files as opaque origins. Inlining is what makes the page work from disk, from a Pages
  deploy and from an email attachment with one code path.
- **Escaping**: a JSON payload inside `<script type="application/json">` breaks on a literal
  `</script>` in the data. Chapter titles will not contain one; regex anchors might. Escape
  `<` as `<` when you serialize — the injector in this section does.
- **Web fonts need a real fallback stack.** The template asks Google Fonts for IBM Plex and
  Source Serif 4 and falls back to system faces. Offline or behind a proxy that blocks it,
  the page must still read correctly — check it with the network disabled. If your target is
  an air-gapped repo, drop the `<link>` and let the fallbacks stand.
- **Responsive to ~400px.** The template collapses the blast-radius grid and the map captions
  at 640px. If you add a column, add its collapse.
- **Accessibility that is actually load-bearing here**: never identify a role by colour
  alone. The chips carry the word, the caption carries the word, and the strip segments are
  real `<button>`s with `aria-label`s so the page maps are reachable without a mouse.

### Injecting the payload

Keep it a build step, not a copy-paste. Six lines:

Use [`example/build-example.py`](example/build-example.py) — it is the reference
implementation of this step and works unchanged against your own payload:

```
./build-example.py --data out.json --out docs/book/xref-page.html
```

Only the `FIELDS` dict at the top is project-specific. It derives `BOOK_LABELS` and
`BOOK_SHORT` from the data rather than hardcoding them, so a new edition appears in the page
the first time it appears in a build rather than the first time someone remembers to add it.
It exits non-zero on an unfilled placeholder, on a row whose `pdf` is missing from `totals`,
and — with `--check` — when the committed page is stale.

The escaping matters: `<` becomes `\u003c` so a regex anchor containing `</script>` cannot
close the JSON block early.

Pasting by hand is how the page and the book get out of sync, which is the exact failure the
page exists to prevent.

---

## 7. Step four — where the page lives

The generated page is a normal build output. Decide deliberately whether it is committed or
ignored, because the two choices buy different things:

| Choice | You get | You pay |
|---|---|---|
| **Commit `xref-page.html`** | Anyone with the repo can open it; no toolchain needed | A large single-line diff on every book build |
| **Gitignore it, commit `XREF.md`** | Clean, reviewable provenance diffs | The page must be regenerated to be read |

The working answer is **both**: commit the Markdown always, and commit the page too if
non-technical readers need it. If the noisy diff bothers you, mark it in `.gitattributes`:

```
docs/book/xref-page.html -diff linguist-generated
```

Three ways to open it, in order of friction:

1. **From disk** — open the file. Every feature works: the data is inlined,
   the only network call is the font stylesheet, and that degrades to system faces.
2. **GitHub Pages** — if the repo already publishes `docs/`, the page is live at
   `<user>.github.io/<repo>/book/xref-page.html` with no extra configuration. Note that a
   public Pages site publishes the page **and its inlined payload**: every chapter title,
   source path and regex anchor in your book. For an internal-edition concordance that is a
   disclosure decision, not a deployment detail.
3. **As a CI artifact** — upload it from the build workflow when you would rather not commit
   it at all. This is the cleanest option for a repo with a private internal edition.

Do not serve it from a branch you force-push, and do not rename the file casually — people
bookmark it.

### Regeneration discipline

The page carries page numbers, so it is **stale the moment you rebuild the book**. Wire it
behind the build, not beside it:

```
python scripts/build-book.py --all                          # your book build
python scripts/locator.py … > out.json                     # locate chapters in the PDFs
python scripts/build-xref-page.py                          # fill the template
```

Commit the Markdown either way. It is what makes a provenance change show up in a pull
request; the page is what makes it legible.

A stale page is worse than no page, because its page numbers look authoritative. Two cheap
guards, both worth adding:

- The page already renders `generated` in the stamp line. Put the **build date in the same
  line as the PDF filename** so a reader comparing it against the newest PDF in the folder
  can see the mismatch.
- In CI, regenerate and fail on a diff. If `XREF.md` changes when nobody edited the book, the
  concordance and the book had drifted, and that is exactly the bug this whole thing exists to
  surface.

---

## 8. Adaptation checklist for a different book project

Work down this list. Nothing above line 6 is optional.

- [ ] Manifest lists chapters in build order, per part, with an `editions` tag on every part
      and entry
- [ ] Every entry resolves to at least one source, via `file`, `source`, or `derived_from`
- [ ] `sources_of()` returns your three roles
- [ ] The locator **imports your builder's resolver** rather than re-parsing the manifest
- [ ] PDF text extraction works on your build (`pypdf`; check a figure-heavy page)
- [ ] `--format json` emits `generated`, `totals`, and `rows[]` per §3
- [ ] Zero `?` pages, or a documented reason for each
- [ ] Template placeholders filled **by a script**, including the two object literals
- [ ] The template's CSS and JS are **byte-identical to the copy you carried in** — diff them
      (the guardrail in [`guardrails.instructions.md`](guardrails.instructions.md))
- [ ] Filter, tabs, strip cross-highlight, and blast-radius click all work at 400px wide
- [ ] Dark and light both render — check `data-theme` and system preference separately
- [ ] Page opens correctly from `file://` with the network disabled
- [ ] Footer says what a page number means and how to regenerate
- [ ] Regeneration is one command chained after the book build
- [ ] Decided, not defaulted: is the page committed, ignored, or a CI artifact (§7)
- [ ] The example still builds: `cd example && ./build-example.py --check`

### Renaming for a non-provenance domain

The page is a **many-to-many join rendered in both directions, with one axis drawn to
scale**. That generalizes past books:

| This page | Generalized | Example |
|---|---|---|
| source file | upstream artifact | a spec, a dataset, a ticket |
| chapter | placed unit | a section, a slide, an endpoint |
| pages | extent on a scaled axis | minutes, tokens, screens |
| role | coupling class | generated / adapted / hand-written |
| blast radius | reverse index by reach | unchanged, and still the best part |

Keep three roles, keep both directions, keep the scaled strip. Those three are what make it
read as a single instrument rather than three tables stacked up.
