---
applyTo: "docs/book/**,book/**,scripts/build-xref*.py,**/locator.py"
description: "Guardrails for the source↔chapter↔page concordance page and its template."
---

# Concordance — guardrails

Canonical procedure: the pattern README. This file is the short list of rules
that hold whenever these paths are touched. It is the single source of truth for them — the
README and the `/concordance` prompt point here rather than restating them.

Adjust the `applyTo` globs above to your repo's layout before using this file.

## The template is an input, not a reference

`xref-page.template.html` is a finished design artifact. Substitute its
`{{PLACEHOLDER}}` tokens and change nothing else.

- Never rewrite, reformat, minify, or "improve" its CSS or JavaScript.
- Never regenerate the page from scratch, and never hand-write a replacement for it.
- Substitute with a **script**. The file is 22KB; retyping it from a partial read silently
  drops the scaled page-map strips, the filter cross-highlighting, the three-way theme
  definition, and the keyboard affordances on the strip segments.
- After filling it, diff the generated page's `<style>` and `<script>` blocks against the
  template's. They must be identical apart from the payload.

If the design genuinely needs to change, change the **template**, deliberately, as its own
commit — never as a side effect of regenerating data.

## The data is generated, never edited

- `pages` values are 1-based PDF page indexes read out of the built PDF. They are not the
  printed folio and they are not derivable from the manifest.
- The page is stale the moment the book is rebuilt. Regenerate it in the same command chain as
  the build, never separately.
- A non-zero `? entries could not be located` warning is a defect to investigate, not a
  cosmetic note. Do not publish a page with unexplained `?` pages.
- Commit the Markdown cross-reference. It is what makes a provenance change reviewable in a
  diff; the page is what makes it legible.

## Provenance roles are a claim, not a label

Three roles only — `sliced`, `adapted`, `authored` — and the strip colour is the most-coupled
role present, in that order. Adding a fourth role means adding a CSS token pair and a chip
class in both themes; do not introduce one casually.

`derived_from` entries must keep resolving. When an anchor stops matching, the fix is a human
re-read of the adaptation, not a quietly updated regex.
