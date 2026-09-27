---
mode: "agent"
description: "Concordance — regenerate the source↔chapter↔page cross-reference and the concordance page from the current book builds. Use after any book build or manifest change."
---

Regenerate the concordance for the current builds.

Guardrails: `.github/instructions/concordance.instructions.md` — read it first and follow it
exactly. Full procedure and design rationale: the pattern README (§6 for the injector, §5 for
the locator when a chapter fails to place).

The one rule that gets violated: `xref-page.template.html` is filled by script,
never rewritten. If you find yourself authoring HTML, CSS, or JavaScript for this task, stop —
you have taken the wrong path.

## Steps

1. Confirm the built PDFs are current. If they are older
   than the manifests or the canon files they slice, stop and report that the book needs
   rebuilding first — do not produce a concordance against a stale build.
2. Regenerate the committed cross-reference with this repo's generator, writing the Markdown
   output to its committed path.
3. Read stderr. On `warning: N entries could not be located in their PDF`, diagnose before
   continuing — the usual cause is a chapter whose first long prose line is a figure caption
   or a table row, and the knock-on effect is that the *next* chapter swallows a large page
   span. Report which entries failed and what you changed.
4. Fill the template and write the page. Substitution is scripted; every placeholder must be
   filled, and `{{BOOK_LABELS}}` / `{{BOOK_SHORT}}` are JS object literals, not strings.
5. Verify before reporting done:
   - `<style>` and `<script>` blocks byte-identical to the template's
   - page opens from `file://` with the network disabled
   - no `{{` left anywhere outside the leading comment
   - stat row, page-map strips, blast radius, both tabs, and the filter cross-highlight all
     render

## Report

State what changed in provenance terms, not file terms: which sources gained or lost chapters,
which chapters moved pages, and any source whose blast radius crossed into a second book. A
diff summary of the Markdown cross-reference is the evidence; say so if nothing changed.
