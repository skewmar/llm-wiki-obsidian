# llm-wiki-obsidian

Personal knowledge graph built on Karpathy's LLM Wiki pattern — Obsidian vault edition.
Ingests emails, WhatsApp exports, notes, and embedded URLs → synthesizes a queryable, visualizable wiki.

→ **[Getting Started](docs/GETTING_STARTED.md)** — installation, Obsidian setup, first run, first query  
→ **[How to Use](docs/HOW_TO_USE.md)** — daily workflow, graph view, Dataview queries, Claude Code querying

> For the generic version (no Obsidian dependency, markdown links): [llm-wiki](https://github.com/skewmar/llm-wiki)

---

## Quick Start

```bash
git clone https://github.com/skewmar/llm-wiki-obsidian && cd llm-wiki-obsidian
pip install -r requirements.txt
cp .env.example .env          # add ANTHROPIC_API_KEY

# Open as Obsidian vault → install Dataview + Templater community plugins

# Drop sources
# raw/emails/   → .txt or .mbox email files
# raw/whatsapp/ → WhatsApp _chat.txt exports
# raw/notes/    → free-form .txt or .md notes

python scripts/fetch_links.py   # fetch URLs embedded in sources
python scripts/ingest.py        # build wiki/ + graph/
# Open graph view in Obsidian (Ctrl/Cmd + G) to see the knowledge graph
claude                          # query via Claude Code
```

---

## Operations

| Command | What it does |
|---|---|
| `python scripts/fetch_links.py` | Extract + fetch all URLs from raw/ sources |
| `python scripts/ingest.py` | Run the full 8-stage ingest pipeline |
| `python scripts/ingest.py --force` | Re-process all sources from scratch |
| `python scripts/lint.py` | Health check + find intersection candidates (wikilink mode) |
| `python scripts/lint.py --generate` | Also draft top comparison pages |
| `python scripts/watch.py` | Always-on: watch raw/ and auto-ingest on new files |
| `python scripts/watch.py --fetch` | Same, but also runs fetch_links first |
| `python scripts/serve.py` | Launch local graph visualization on localhost:5050 |

---

## Architecture

```
raw/           ← Drop sources here (immutable, hidden from Obsidian)
wiki/          ← LLM-synthesized knowledge (you read, LLM writes)
  index.md     ← Master catalog of all entities + concepts
  log.md       ← Append-only ingest history
  overview.md  ← High-level synthesis
  _templates/  ← Templater templates for manual note creation
  entities/    ← One file per person/company/project  [blue in graph]
  concepts/    ← One file per idea/framework/argument [purple in graph]
  summaries/   ← One file per source document         [green in graph]
  comparisons/ ← Cross-entity synthesis pages         [orange in graph]
graph/         ← Claude Code routing layer (NOT Obsidian graph)
  interfaces/  ← router, temporal, disambiguation, intersections
  domains/     ← Lean domain manifests (auto-generated)
launchagent/   ← macOS LaunchAgent for always-on watching
docs/          ← Getting started + usage reference
```

---

## Key Design Decisions

| Decision | Why |
|---|---|
| `[[wikilinks]]` only | Only wikilinks create edges in Obsidian's graph view |
| `raw/` hidden from Obsidian | Prevents source files from polluting the graph |
| Always additive ingest | `[evolved to]` markers preserve history — never overwrites |
| Content-hash dedup | Same file re-added with different name is skipped |
| Karpathy-first (no RAG) | Pre-synthesized wiki beats RAG at <500 sources |

---

## Example Claude Code Queries

After running `ingest.py`, open `claude` from the repo root:

```
Who are the key people in my email thread?
How has thinking on [topic] evolved over time?
What connects [person A] and [person B]?
What open questions does my knowledge base raise?
```

---

## Reference
- [Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [Claude Code](https://claude.ai/code)
- [Generic version](https://github.com/skewmar/llm-wiki)
