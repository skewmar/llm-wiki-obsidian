# Getting Started

This guide walks you through installation, Obsidian setup, your first ingest run, and your first query.

---

## Prerequisites

- **Python 3.9+** — `python3 --version`
- **Anthropic API key** — get one at https://console.anthropic.com
- **Obsidian** — download at https://obsidian.md (free)
- **Claude Code** — install at https://claude.ai/code (for querying the wiki)
- **Git** — to clone the repo

---

## 1. Install

```bash
git clone https://github.com/skewmar/llm-wiki-obsidian
cd llm-wiki-obsidian

pip install -r requirements.txt

cp .env.example .env
# Open .env and replace sk-ant-your-key-here with your real key
```

---

## 2. Open as an Obsidian Vault

1. Open Obsidian
2. **File → Open folder as vault**
3. Select the `llm-wiki-obsidian` repo root
4. Obsidian will prompt to trust the vault — click **Trust and enable plugins** (or enable manually in settings)

**Install community plugins:**
1. Settings (gear icon) → Community plugins → Turn off Restricted mode
2. Browse → search **Dataview** → Install → Enable
3. Browse → search **Templater** → Install → Enable

These are already configured in `.obsidian/plugins/`. You just need to install the plugin binaries from the community store.

> `raw/` is automatically hidden from Obsidian's graph view and search via `.obsidian/app.json`. You'll never see raw source files cluttering your graph.

---

## 3. Drop Your Sources

The `raw/` directory is your drop zone. The pipeline reads from here and never modifies these files.

```
raw/
  emails/     ← .txt or .mbox email files
  whatsapp/   ← WhatsApp export (_chat.txt)
  notes/      ← free-form .txt or .md notes
```

**Email**: Export your email thread as plain text or .mbox. A single .txt with all emails pasted works fine for a long thread.

**WhatsApp**: In the app → chat → ⋮ → Export chat → Without media → save the `_chat.txt` file.

**Notes**: Any .txt or .md files. Split sections with `---` or markdown headings for better chunking.

---

## 4. Fetch Embedded URLs (optional but recommended)

```bash
python scripts/fetch_links.py
```

Extracts all `https://` URLs from your sources, skips noise (social/calendar/unsubscribe), and saves each page as text to `raw/fetched/`. Only fetches new URLs on re-runs.

---

## 5. Run the Ingest Pipeline

```bash
python scripts/ingest.py
```

The pipeline runs 8 stages: parse → extract (Haiku) → diff → entity files (Sonnet) → concept files → summaries → domain manifests → index/log/overview.

**What gets created:**
```
wiki/
  index.md        ← master catalog — start here
  overview.md     ← high-level synthesis of everything
  log.md          ← one entry per run, append-only
  entities/       ← one .md per person/company/project
  concepts/       ← one .md per recurring idea or framework
  summaries/      ← one .md per source document
```

**Every file uses `[[wikilinks]]`** for internal references. These are the edges that appear in Obsidian's graph view.

Cost estimate: ~$0.10–0.30 for a 120-email thread with prompt caching on.

---

## 6. Explore the Graph in Obsidian

Open the graph view: **Ctrl/Cmd + G** (or View → Open graph view)

Node colors:
- 🔵 **Blue** — entities (`wiki/entities/`)
- 🟣 **Purple** — concepts (`wiki/concepts/`)
- 🟠 **Orange** — comparisons (`wiki/comparisons/`)
- 🟢 **Green** — summaries (`wiki/summaries/`)

Nodes cluster naturally by shared wikilinks — entities that appear together in multiple summaries will cluster together. Concepts appear as hubs connecting multiple entities.

**Graph tips:**
- Drag to pan, scroll to zoom
- Click a node to open that file in the main editor
- Use the filter bar to focus on a specific domain or file type
- `path:wiki/entities` in the filter shows only entity nodes

---

## 7. Query via Obsidian (Dataview)

Open any note and add a Dataview code block to query across your wiki:

```dataview
TABLE domain, status FROM "wiki/entities"
SORT domain ASC
```

```dataview
TABLE domain, maturity FROM "wiki/concepts"
WHERE maturity = "developing" OR maturity = "stable"
```

```dataview
TABLE date_range, source_type FROM "wiki/summaries"
SORT date_range DESC
```

---

## 8. Query via Claude Code

```bash
# From the repo root
claude
```

`CLAUDE.md` loads automatically. Try these prompts:

```
Who are the key people in my email thread?
```
```
What is the main thesis being discussed?
```
```
How has the thinking on [topic] evolved over time?
```
```
What connections exist between [person A] and [person B]?
```

Claude Code routes through `graph/interfaces/router.md`, loads only the relevant wiki/ files, and answers from pre-synthesized content.

---

## 9. Run the Health Check

```bash
python scripts/lint.py
```

Checks broken wikilinks, orphaned files, missing temporal markers, stale summaries. Finds entity pairs that co-occur frequently but have no synthesis page. To generate comparison pages:

```bash
python scripts/lint.py --generate
```

---

## 10. Add More Sources Anytime

Drop new files in `raw/` and run `python scripts/ingest.py`. Only new files are processed. Existing entity files are updated with `[evolved to]` markers — never overwritten.

---

## Always-On Mode

### Terminal
```bash
python scripts/watch.py --fetch
# Watches raw/ with 30s debounce, auto-triggers fetch_links + ingest
```

### macOS LaunchAgent (background, survives reboot)
```bash
REPO=$(pwd)
sed -i '' "s|REPO_PATH|$REPO|g" launchagent/com.skewmar.knowledgegraph.plist
cp launchagent/com.skewmar.knowledgegraph.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.skewmar.knowledgegraph.plist
```

Check it's running:
```bash
launchctl list | grep skewmar
tail -f launchagent/watch.log
```

---

## Troubleshooting

**Graph view shows no edges** — Make sure all internal links are `[[wikilinks]]`, not `[text](path.md)`. Only wikilinks create graph edges in Obsidian. Run `python scripts/lint.py` to check for broken links.

**raw/ files appear in graph** — Check `.obsidian/app.json` has `"raw/"` in `userIgnoreFilters`. If Obsidian cached the file list, restart Obsidian.

**Dataview shows no results** — Enable the Dataview plugin in Settings → Community plugins. YAML frontmatter must be valid (no tabs, proper indentation).

**"Nothing new" on first run** — Run with `--force` to bypass the content-hash registry.

**API errors** — Verify your key in `.env`. Rate limit errors retry automatically with exponential backoff.

**Claude Code not loading CLAUDE.md** — Run `claude` from the repo root directory.
