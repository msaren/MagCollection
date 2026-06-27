# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

MagCollection is a web app for browsing a magazine collection. **No application code exists yet** — the repository currently contains only:

- `collections/` — the actual magazine content (PDFs)
- `DESIGN.md` — a design-system spec for the UI to be built
- `README.md` — one-line project description

There is no build tooling, package manifest, framework choice, or test setup yet. When starting implementation, check with the user about stack choices rather than assuming one.

## Content structure (`collections/`)

Magazines are organized as one subdirectory per title under `collections/`, containing the issue PDFs:

```
collections/<Magazine Title>/<Magazine Title> - Issue <N> - <Month-Month Year>.pdf
```

Example: `collections/ZZAP! Amiga/ZZAP! AMIGA - Issue 17 - July-August 2024.pdf`

Naming is not perfectly consistent across magazines (e.g. `collections/Skrolli/2026.1.untsunts.pdf` uses a different scheme: `<year>.<issue>.<title-slug>.pdf`). Any code that indexes/parses this directory must handle both naming conventions rather than assuming one fixed format. The directory name is the canonical magazine title/series; filenames are not guaranteed to be machine-parseable for issue metadata in the same way.

## Design system (`DESIGN.md`)

`DESIGN.md` is a token-based design spec (YAML frontmatter + Markdown) modeled on Anthropic's brand language — warm cream canvas, coral primary accent, dark navy product surfaces, serif display type (Copernicus/Tiempos Headline substitute) paired with humanist sans body (StyreneB/Inter). It defines colors, typography, spacing, border-radius, and named components (e.g. `feature-card`, `code-window-card`, `pricing-tier-card`) as reusable tokens referenced like `{colors.primary}` / `{component.button-primary}`.

When building UI:
- Pull all values from the tokens defined in `DESIGN.md` rather than hardcoding hex/px values.
- Follow the documented Do's/Don'ts and responsive breakpoints in that file rather than inventing new patterns.
- This spec was written for a generic Anthropic-styled marketing site and reuses some component names (pricing tiers, connector tiles) that may not map directly onto magazine-browsing UI — treat it as a token/style source, not a literal page-by-page spec for this app.
