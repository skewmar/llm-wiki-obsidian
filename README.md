# llm-wiki-obsidian

Personal knowledge graph built on Karpathy's LLM Wiki pattern — Obsidian vault edition.
Ingests emails, WhatsApp exports, notes, and embedded URLs → synthesizes a queryable, visualizable wiki.

This repo is also an Obsidian vault. Open the root folder directly in Obsidian.

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env          # add your ANTHROPIC_API_KEY

# Drop sources
# raw/emails/   → email .txt or .mbox files
# raw/whatsapp/ → WhatsApp _chat.txt exports
# raw/notes/    → free-form .txt or .md notes

python scripts/fetch_links.py   # fetch URLs embedded in sources
python scripts/ingest.py        # build wiki/ + graph/
```

Then open Claude Code in this directory — CLAUDE.md loads automatically.

## Obsidian Setup

1. **Open as vault**: File → Open folder as vault → select this repo root
2. **Install community plugins**: Settings → Community plugins → Browse
   - Install **Dataview** (for querying frontmatter across notes)
   - Install **Templater** (for the templates in `wiki/_templates/`)
3. **Enable plugins**: Toggle both on after install
4. **Graph view**: Open (Ctrl/Cmd + G) — entities blue, concepts purple, comparisons orange, summaries green

> `raw/` is hidden from Obsidian search and graph view automatically via `.obsidian/app.json`

## Operations

| Command | What it does |
|---|---|
| `python scripts/fetch_links.py` | Extract + fetch all URLs from raw/ sources |
| `python scripts/ingest.py` | Run the full 8-stage ingest pipeline |
| `python scripts/ingest.py --force` | Re-process all sources from scratch |
| `python scripts/lint.py` | Health check + find intersection candidates |
| `python scripts/lint.py --generate` | Also draft top comparison pages |
| `python scripts/watch.py` | Always-on: watch raw/ and auto-ingest on new files |
| `python scripts/watch.py --fetch` | Same, but also runs fetch_links first |

## Always-On Background Watcher (macOS)

```bash
# Set repo path and install LaunchAgent
REPO=$(pwd)
sed -i '' "s|REPO_PATH|$REPO|g" launchagent/com.skewmar.knowledgegraph.plist
cp launchagent/com.skewmar.knowledgegraph.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.skewmar.knowledgegraph.plist
```

See `launchagent/README.md` for status check and uninstall instructions.

## Architecture

```
raw/           ← Drop sources here (immutable, hidden from Obsidian)
wiki/          ← LLM-synthesized knowledge (you read, LLM writes)
  index.md     ← Master catalog of all entities + concepts
  log.md       ← Append-only ingest history
  overview.md  ← High-level synthesis
  _templates/  ← Templater templates for manual note creation
  entities/    ← One file per person/company/project
  concepts/    ← One file per idea/framework/argument
  summaries/   ← One file per source document
  comparisons/ ← Cross-entity synthesis pages
graph/         ← Claude Code routing layer (NOT Obsidian graph)
  interfaces/  ← router, temporal, disambiguation, intersections
  domains/     ← Lean domain manifests (auto-generated)
```

## Dataview Example Queries

Open any note in Obsidian and paste:

```dataview
TABLE domain, status FROM "wiki/entities"
SORT domain ASC
```

```dataview
TABLE domain, maturity FROM "wiki/concepts"
WHERE maturity = "stable"
```

## Key Design Decisions

- **[[wikilinks]] only** — standard markdown links don't appear in Obsidian's graph view
- **`raw/` invisible to Obsidian** — excluded via app.json, won't pollute graph or search
- **Always additive** — ingest.py never overwrites; uses `[evolved to]` markers
- **Content-hash dedup** — same file re-added with different name is skipped
- **Karpathy-first** — wiki/ is pre-synthesized, not RAG over raw chunks

## Reference
- Karpathy's LLM Wiki: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Claude Code: https://claude.ai/code
- Generic version (no Obsidian): https://github.com/skewmar/llm-wiki
