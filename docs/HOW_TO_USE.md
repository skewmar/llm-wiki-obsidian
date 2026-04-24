# How to Use

Day-to-day reference for operating the knowledge graph, using Obsidian's graph view, and querying effectively.

---

## The Mental Model

```
You drop sources → pipeline synthesizes wiki/ → graph view + Claude Code answer from wiki/
```

- **`raw/`** — immutable archive, hidden from Obsidian, never modified after parsing
- **`wiki/`** — LLM-synthesized knowledge, you read it, LLM writes it, visible in graph
- **`graph/interfaces/`** — routing layer, always loaded by Claude Code
- **`[[wikilinks]]`** — the only link format that creates edges in Obsidian's graph view

---

## Graph Visualization (localhost)

In addition to Obsidian's built-in graph view, you can run a standalone web visualization:

```bash
python scripts/serve.py
# Opens http://localhost:5050 in your browser automatically
```

What you get:
- **Force-directed graph** — nodes pull toward connected neighbors, clusters emerge naturally
- **Node colors** — blue = entities, purple = concepts, orange = comparisons, green = summaries
- **Node size** — larger = more connections (hub nodes stand out)
- **Click any node** — right panel shows description, all connected nodes, and file content
- **Click a connection** in the detail panel to jump to that node
- **Search bar** — highlights matching nodes by name, description, or domain
- **Type filters** — toggle entities/concepts/comparisons/summaries on/off
- **Zoom controls** — ⊡ to auto-fit the whole graph, + / − to zoom

This is useful for sharing a snapshot with others (no Obsidian required) or for a browser-based view alongside Claude Code.

After re-running `ingest.py`, hit `/api/refresh` to reload the graph without restarting:
```
http://localhost:5050/api/refresh
```

---

## Daily Workflow

**Adding new sources:**
```bash
# Drop file in raw/emails/, raw/whatsapp/, or raw/notes/
python scripts/fetch_links.py   # optional: fetch embedded URLs
python scripts/ingest.py        # process new files, update wiki/
```

**Always-on (terminal):**
```bash
python scripts/watch.py --fetch
```

**Always-on (background, macOS):**
```bash
launchctl list | grep skewmar   # check if LaunchAgent is running
tail -f launchagent/watch.log   # watch the log
```

**Health check:**
```bash
python scripts/lint.py           # issues + intersection candidates
python scripts/lint.py --generate  # also draft comparison pages
```

---

## Querying via Claude Code

```bash
claude  # from repo root — CLAUDE.md loads automatically
```

### Entity questions
```
What do I know about [person name]?
What is [company]'s current status?
Who are the key people involved in [project]?
```

### Concept questions
```
What is the main argument around [concept]?
How has thinking on [concept] evolved?
Where does [concept] show up across my sources?
```

### Temporal questions

Temporal markers (`[as of YYYY-MM]`, `[early thinking]`, `[evolved to]`) make these work:
```
How has [person]'s position on [topic] changed over time?
What was the original thinking on [concept], and where did it land?
What's the most recent status of [project]?
What has changed recently?
```

### Intersection questions
```
What do [person A] and [person B] have in common?
How does [concept X] relate to [concept Y]?
What are the non-obvious connections across my knowledge base?
```

---

## Using Obsidian Effectively

### Graph View (Ctrl/Cmd + G)

Node colors match file types:
- 🔵 Blue = entities, 🟣 Purple = concepts, 🟠 Orange = comparisons, 🟢 Green = summaries

**What the edges mean:** Two nodes are connected if one has a `[[link]]` pointing to the other. Entity nodes cluster with the concepts that reference them. Summary nodes connect to every entity and concept mentioned in that source.

**Useful filters:**
```
path:wiki/entities        # only entity nodes
path:wiki/concepts        # only concept nodes
path:wiki/comparisons     # only synthesis pages
```

**Local graph:** With a file open, right-click its tab → Open local graph. Shows just the direct connections of that one note — useful for exploring one entity or concept.

### Dataview Queries

Paste these into any note to build live dashboards:

**All entities by domain:**
```dataview
TABLE domain, status FROM "wiki/entities"
SORT domain ASC
```

**Stable concepts only:**
```dataview
TABLE domain, maturity FROM "wiki/concepts"
WHERE maturity = "stable"
SORT domain ASC
```

**Recent sources:**
```dataview
TABLE date_range, source_type FROM "wiki/summaries"
SORT date_range DESC
LIMIT 10
```

**People only:**
```dataview
TABLE domain, status FROM "wiki/entities"
WHERE subtype = "person"
```

**Seed concepts (least developed — candidates for deepening):**
```dataview
TABLE domain FROM "wiki/concepts"
WHERE maturity = "seed"
```

### Templater (for manual notes)

To create a new entity or concept note using the template:
1. Create a new note in `wiki/entities/` or `wiki/concepts/`
2. Open the command palette (Ctrl/Cmd + P)
3. Run: **Templater: Insert template**
4. Select `entity` or `concept`

The template auto-fills the slug from the filename and today's date.

---

## Understanding Wiki Files

### Entity files (`wiki/entities/slug.md`)

| Section | What it contains |
|---|---|
| Frontmatter | type, subtype, domain, slug, status |
| Opening `>` | Most specific, surprising fact first |
| Key Facts | Bullets with `[as of YYYY-MM]` |
| Relationships | Table with `[[wikilinks]]` to other entities/concepts |
| How Thinking Has Evolved | `[early thinking]` → `[evolved to]` chain |
| Open Questions | Unresolved questions this entity raises |
| Answers Questions | What you can ask this file |
| Sources | `[[summary-slug]]` links to source files |

### Concept files (`wiki/concepts/slug.md`)

Same structure, but the key section is **The Argument** — the full description with evolution markers.

### Comparison files (`wiki/comparisons/a-x-b.md`)

Generated by `lint.py --generate` for entity pairs that co-occur in 3+ sources. Contains: The Connection, Where They Diverge, Intersectional Insight. These are high-value synthesis pages — read them to find non-obvious connections.

---

## Temporal Markers

| Marker | Meaning | When to trust it |
|---|---|---|
| `[as of YYYY-MM]` | Confirmed that month | High — check date |
| `[current]` | Most recent confirmed state | High — most up-to-date |
| `[early thinking]` | Initial position | Low — likely superseded |
| `[evolved to]` | Updated position | High — supersedes early thinking |
| `[inferred]` | Derived from context | Medium — logical but not explicit |
| `[unconfirmed]` | Heard but unverified | Low — do not cite as fact |
| `[archived]` | No longer active | Historical only |

---

## The Routing Layer

`graph/interfaces/` files are always loaded into Claude Code context (~4KB total):

- **`router.md`** — maps question types to specific wiki/ files (load entity first vs. concept first vs. domain manifest)
- **`temporal.md`** — rules for time-aware queries (which markers map to which questions)
- **`disambiguation.md`** — what to do when two things share a name
- **`intersections.md`** — how to find and surface connections across domains; auto-updated by `lint.py`

`graph/domains/` — auto-generated per-domain manifests listing slugs. CLAUDE.md auto-adds `@graph/domains/X.md` imports after each ingest run.

---

## Wikilink Discipline

This is the most important rule for the Obsidian version:

**Only `[[wikilinks]]` create graph edges.** Standard markdown links `[text](path.md)` are invisible to the graph view.

The pipeline enforces this automatically (`USE_WIKILINKS = True` in `ingest.py`). For manual notes, always use `[[slug]]` when linking to entities or concepts.

`lint.py` checks for broken wikilinks by default. Run it after adding manual notes.

---

## Deduplication

Sources are tracked by content hash (MD5):
- Renaming a file won't re-process it
- Adding the same file twice won't re-process it
- Editing a file (changing content) will trigger re-processing

To inspect the registry: `python -c "import json; print(json.load(open('.processed_hashes')))"`

To force a full re-process: `rm .processed_hashes && python scripts/ingest.py`

---

## Cost Reference

| Operation | Model | ~Cost |
|---|---|---|
| 120-email thread extraction | Haiku (cached) | ~$0.02 |
| 10 entity synthesis files | Sonnet | ~$0.10 |
| 10 concept synthesis files | Sonnet | ~$0.08 |
| Source summary (per file) | Sonnet | ~$0.01 |
| Comparison page | Sonnet | ~$0.01 each |

Prompt caching cuts Stage 2 cost ~90% for large email threads.
