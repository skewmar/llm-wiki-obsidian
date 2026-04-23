# Personal Knowledge Graph — Claude Code Harness (Obsidian Edition)

## Primary Architecture: Karpathy LLM Wiki
Memory is synthesis, not retrieval. `wiki/` is pre-synthesized knowledge.
`raw/` is the immutable archive. Never answer from `raw/` — always from `wiki/`.
Reference: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

## How to Answer Questions
1. Read @graph/interfaces/router.md — identify domain and relevant wiki/ files
2. Check @wiki/index.md — find the specific entity/concept slugs to load
3. Load only the relevant entity/concept files (on demand, not loaded here)
4. Apply @graph/interfaces/temporal.md if the question involves time or evolution
5. Apply @graph/interfaces/disambiguation.md if two concepts seem to overlap
6. Apply @graph/interfaces/intersections.md if seeking connections across topics
7. Cite wiki/ filenames as sources — never cite raw/ files

## Always Loaded (~4KB total)
@graph/interfaces/router.md
@graph/interfaces/temporal.md
@graph/interfaces/disambiguation.md
@graph/interfaces/intersections.md
@wiki/index.md
@wiki/overview.md

## Domain Manifests (always loaded — populated by ingest.py)

## Entity/concept files: NOT loaded here. Load on demand via wiki/index.md.

## Operations
- Ingest new sources:    `python scripts/ingest.py`
- Fetch URLs from email: `python scripts/fetch_links.py`
- Health check + intersections: `python scripts/lint.py`
- Always-on watching:   `python scripts/watch.py`

## Wiki Writing Rules (when maintaining wiki/)
- Use [[Slug]] wikilinks for ALL internal references — only wikilinks create Obsidian graph edges
- Mark temporal claims: [as of YYYY-MM] [early thinking] [evolved to] [current]
- Lead with the most specific, surprising fact — not background
- Never overwrite existing content — use [evolved to] markers to preserve history
- Never fabricate — use [inferred] or [unconfirmed] for uncertain claims
- File valuable query answers back into wiki/comparisons/ as new pages
