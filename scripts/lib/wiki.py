import re
from pathlib import Path
from datetime import datetime

# Obsidian version uses wikilinks — [[slug]] creates graph edges in Obsidian
LINK_FORMAT = "wikilink"


def load_index(index_file: Path) -> dict:
    result = {"entities": {}, "concepts": {}}
    if not index_file.exists():
        return result

    text = index_file.read_text()
    section = None
    for line in text.split("\n"):
        if "## Entities" in line:
            section = "entities"
        elif "## Concepts" in line:
            section = "concepts"
        elif line.startswith("| ") and section:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 3 or parts[1].startswith("-"):
                continue
            m = re.search(r"\[([^\]]+)\]\([^)]+/([^/)]+)\.md\)", parts[1])
            wm = re.search(r"\[\[([^\]|]+)", parts[1])
            if m:
                result[section][m.group(2)] = parts[2] if len(parts) > 2 else ""
            elif wm:
                result[section][wm.group(1)] = parts[2] if len(parts) > 2 else ""
    return result


def update_index(wiki_dir: Path, knowledge):
    def _rows(subdir: str, link_prefix: str) -> list:
        rows = []
        d = wiki_dir / subdir
        if not d.exists():
            return rows
        for f in sorted(d.glob("*.md")):
            if f.name.startswith("_"):
                continue
            desc = ""
            for line in f.read_text().split("\n"):
                if line.startswith(">"):
                    desc = line.lstrip("> ").strip()
                    break
            if LINK_FORMAT == "wikilink":
                link = f"[[{f.stem}]]"
            else:
                link = f"[{f.stem}]({link_prefix}/{f.name})"
            rows.append(f"| {link} | {desc} |")
        return rows

    e_rows = _rows("entities", "entities")
    c_rows = _rows("concepts", "concepts")
    s_rows = []
    summaries_dir = wiki_dir / "summaries"
    if summaries_dir.exists():
        for f in sorted(summaries_dir.glob("*.md")):
            if f.name.startswith("_"):
                continue
            if LINK_FORMAT == "wikilink":
                link = f"[[{f.stem}]]"
            else:
                link = f"[{f.stem}](summaries/{f.name})"
            s_rows.append(f"| {link} |")

    nl = "\n"
    content = f"""# Wiki Index
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Entities
| Slug | Description |
|---|---|
{nl.join(e_rows) or '| (none yet) | |'}

## Concepts
| Slug | Description |
|---|---|
{nl.join(c_rows) or '| (none yet) | |'}

## Summaries
| Source |
|---|
{nl.join(s_rows) or '| (none yet) |'}
"""
    (wiki_dir / "index.md").write_text(content)


def append_log(log_file: Path, entry: dict):
    ts = entry.get("timestamp", datetime.now().isoformat())
    sources = entry.get("sources_processed", [])
    created = entry.get("entities_created", []) + entry.get("concepts_created", [])
    updated = entry.get("entities_updated", []) + entry.get("concepts_updated", [])

    log_entry = (
        f"\n## [{ts[:10]}] ingest | {len(sources)} source(s)\n\n"
        f"**Sources**: {', '.join(Path(s).name for s in sources) or 'none'}  \n"
        f"**Created**: {', '.join(created) or 'none'}  \n"
        f"**Updated**: {', '.join(updated) or 'none'}\n"
    )

    if not log_file.exists() or log_file.stat().st_size == 0:
        log_file.write_text("# Ingest Log\n\nAppend-only record of all ingest operations.\n")

    with open(log_file, "a") as f:
        f.write(log_entry)


def load_file(file_path: Path) -> str:
    return file_path.read_text() if file_path.exists() else ""


def write_file(file_path: Path, content: str):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)


def update_temporal_anchors(temporal_file: Path, processed_files: list):
    if not temporal_file.exists():
        return
    text = temporal_file.read_text()
    today = datetime.now().strftime("%Y-%m-%d")
    text = re.sub(r"- Last ingest run: .*", f"- Last ingest run: {today}", text)
    if processed_files:
        text = re.sub(
            r"- Most recent source: .*",
            f"- Most recent source: {Path(processed_files[-1]).name}",
            text,
        )
    temporal_file.write_text(text)
