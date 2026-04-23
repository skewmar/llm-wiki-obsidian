# Methodology

## Primary Architecture: Karpathy's LLM Wiki Pattern

Source: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

The core insight: **memory should be synthesis, not retrieval.**

Traditional RAG re-discovers knowledge from scratch on every query — the LLM reads raw
chunks and assembles an answer each time. Nothing accumulates. This system instead has the
LLM pre-compile knowledge into a maintained wiki during ingest. Queries hit pre-synthesized
pages rather than raw source fragments.

The result: richer answers, cross-references already in place, contradictions already
flagged, and compound value as sources accumulate.

## The Three Layers

**raw/** — Immutable archive. You drop files here. LLM reads but never modifies.
This is your ground truth. If the wiki is wrong, raw/ lets you regenerate it.

**wiki/** — LLM-maintained synthesis. The LLM creates and updates all files here.
You read wiki/. The LLM writes wiki/. You never edit wiki/ files directly.

**CLAUDE.md + graph/interfaces/** — Schema and routing. Tells Claude Code how the wiki
is structured, how to route questions to the right files, and how to reason about time.
This layer is small (~4KB), always loaded, and never contains entity detail.

## Add-On Layer 1: Verizon-Style Routing (graph/interfaces/)

Inspired by Atlan's Verizon OneEx ontology approach: structured routing files that tell
the agent which file to load for which type of question, before scanning all entities.

`router.md` — maps question signals to entity/concept files
`temporal.md` — maps time language to the right markers and query strategy
`disambiguation.md` — resolves ambiguous entity/concept matches
`intersections.md` — routes questions about connections across domains

## Add-On Layer 2: Claude Code Best Practices

`CLAUDE.md` stays under 200 lines with `@path` imports for the routing layer.
Entity and concept files are NOT imported at startup — they load on demand.
This keeps the always-loaded context small (~4KB) while entity detail is available
when needed, avoiding the "everything in one context dump" failure mode.

## Obsidian Integration

This is also an Obsidian vault. Key rules:
- **[[wikilinks]] only** for internal references — standard markdown links do NOT create
  graph edges in Obsidian's graph view
- YAML frontmatter on all wiki/ files enables Dataview queries
- `wiki/_templates/` contains Templater-compatible templates for manual note creation
- `.obsidian/` config committed (except workspace): graph coloring, excluded files, plugins

## What Goes Where

| Item | Location |
|---|---|
| New source document | `raw/` — drop and run ingest.py |
| Named person | `wiki/entities/[slug].md` |
| Named company or project | `wiki/entities/[slug].md` |
| Recurring idea or framework | `wiki/concepts/[slug].md` |
| Source document summary | `wiki/summaries/[slug].md` |
| Cross-entity synthesis | `wiki/comparisons/[a]-x-[b].md` |
| Topic cluster routing | `graph/domains/[domain].md` |

## Anti-Patterns

**Monolithic context file** — Never create a single file that dumps all entities.
It becomes unmaintainable and bloats the context window.

**Duplicate representations** — wiki/ is the source of truth. raw/ is the archive.
Never have both carry the same synthesized content.

**Empty interfaces/** — Every routing file must have real rules before committing.

**Loading all entities at startup** — Entity files are the detail layer, on demand only.

**Answering from raw/** — raw/ is unprocessed. wiki/ is always the answer source.

**Overwriting on update** — Always append with [evolved to] markers. Preserve history.

**Markdown links in Obsidian wiki** — Use [[wikilinks]]. Markdown links won't appear
in the graph view and will silently break the visualization.

## Scale Guidance (from Karpathy)

- < 100 sources: wiki/index.md is sufficient for navigation, no search needed
- 100–500 sources: this system works optimally
- 500+ sources: consider adding vector search alongside the wiki index

## The Role Division

You: curate sources, ask good questions, direct analysis, decide what matters.
LLM: summarize, cross-reference, file, maintain, surface connections, do the bookkeeping.
