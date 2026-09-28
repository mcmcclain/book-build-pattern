# book-build-patterns

Reusable patterns for books and documentation that are **compiled from source files** rather
than typed into one manuscript — where chapters are sliced out of canon documents at build
time, several editions ship from one manifest, and a one-line edit upstream can move a dozen
pages across three books.

Each pattern is self-contained: a README that explains the design and the reasoning, the
working files to copy, agent guardrails, and a runnable example with synthetic data so you can
see it work before adopting it.

## Patterns

| Pattern | What it does | Status |
|---|---|---|
| [**concordance**](patterns/concordance/) | Source ↔ chapter ↔ page cross-reference. Answers *what is this chapter made of* and *if I edit this file, what breaks* — with page-map strips drawn to scale against each built PDF. | Working, with example |

## What "a pattern" means here

Not a library, and not a framework. Each one is a **design plus the files that implement it**,
written to be copied into your repo and adapted. There is nothing to install and nothing to
depend on. That is deliberate: these solve problems that are 80% shaped by your own manifest
format, and a dependency would fight you over the other 20%.

Every pattern carries three things, because they have genuinely different lifecycles:

| Artifact | Loaded | Contains |
|---|---|---|
| `README.md` | Once, while building | The design, the reasoning, the failure modes |
| `guardrails.instructions.md` | Always, on the paths that matter | The short list of rules that must hold every time |
| `*.prompt.md` | On demand | The runbook for doing the thing today |

Splitting them is the point. A guardrail buried inside 500 lines of design rationale is a
guardrail nobody loads — and the rules most likely to be violated are the ones that read as
obvious.

The agent files are written for [GitHub Copilot's](https://docs.github.com/copilot) instruction
formats — `.github/instructions/*.instructions.md` with `applyTo:` globs, and
`.github/prompts/*.prompt.md` invoked as `/name`. They are plain Markdown with frontmatter, so
they port to any agent that reads repo instructions; adjust the frontmatter keys and the globs.

## Using one

```
git clone https://github.com/mcmcclain/book-build-pattern
cd book-build-pattern/patterns/concordance
cd example && ./build-example.py && open index.html
```

Then read that pattern's README and its §0 for the file-by-file copy list.

## Contributing

Issues and PRs welcome, particularly worked adaptations to other manifest formats and other
book builders — the patterns were extracted from a WeasyPrint/Markdown pipeline and the
assumptions that leaked from it are worth finding.

## License

[MIT](LICENSE). Attribution is not required but is appreciated — a link back helps people find
the reasoning behind the files they are copying.
