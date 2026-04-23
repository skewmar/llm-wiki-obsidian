#!/usr/bin/env python3
"""
ingest.py — Main pipeline: raw/ → wiki/ + graph/

Stages:
  0. Setup + dedup check
  1. Parse raw sources → Chunks
  2. Extract entities + concepts via Claude Haiku (batched)
  3. Diff against wiki/index.md
  4. Generate/update wiki/entities/
  5. Generate/update wiki/concepts/
  6. Generate wiki/summaries/
  7. Regenerate graph/domains/ manifests
  8. Update index, log, overview, temporal anchors

Usage:
    python scripts/ingest.py           # Process new sources only
    python scripts/ingest.py --force   # Re-process everything
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "raw"
WIKI_DIR = ROOT / "wiki"
GRAPH_DIR = ROOT / "graph"

from lib.parsers import (parse_email_thread, parse_whatsapp_export,
                         parse_notes, parse_fetched_url)
from lib.dedup import get_unprocessed_files, mark_processed
from lib.llm import (extract_knowledge, synthesize_entity, synthesize_concept,
                     summarize_source, synthesize_overview, generate_domain_manifest)
from lib.wiki import (load_index, update_index, append_log,
                      load_file, write_file, update_temporal_anchors)

USE_WIKILINKS = True  # Obsidian version — [[wikilinks]] create graph edges


def classify_file(f: Path) -> str:
    s = str(f).lower()
    if "emails" in s or f.suffix == ".mbox":
        return "email"
    if "whatsapp" in s:
        return "whatsapp"
    if "fetched" in s:
        return "fetched_url"
    return "notes"


def run_ingest(force: bool = False):
    print("=" * 60)
    print("🔄 LLM Wiki (Obsidian) — Ingest Pipeline")
    print("=" * 60)

    for d in [WIKI_DIR / "entities", WIKI_DIR / "concepts",
              WIKI_DIR / "summaries", WIKI_DIR / "comparisons",
              GRAPH_DIR / "interfaces", GRAPH_DIR / "domains"]:
        d.mkdir(parents=True, exist_ok=True)

    # Stage 0
    print("\n📂 Stage 0: Scanning for new sources...")
    unprocessed = get_unprocessed_files(RAW_DIR, force=force)
    if not unprocessed:
        print("  ✅ Nothing new. Use --force to re-process all sources.")
        return
    print(f"  → {len(unprocessed)} source(s) to process")
    for f in unprocessed:
        print(f"     • {f.relative_to(ROOT)}")

    # Stage 1
    print("\n📖 Stage 1: Parsing sources...")
    all_chunks = []
    for f in unprocessed:
        try:
            ftype = classify_file(f)
            if ftype == "email":
                chunks = parse_email_thread(f)
            elif ftype == "whatsapp":
                chunks = parse_whatsapp_export(f)
            elif ftype == "fetched_url":
                chunks = parse_fetched_url(f)
            else:
                chunks = parse_notes(f)
            all_chunks.extend(chunks)
            print(f"  → {f.name}: {len(chunks)} chunk(s)")
        except Exception as e:
            print(f"  ⚠️  {f.name}: {e}")

    if not all_chunks:
        print("  ⚠️  No chunks produced.")
        return
    print(f"  → Total: {len(all_chunks)} chunks")

    # Stage 2
    print(f"\n🧠 Stage 2: Extracting knowledge ({len(all_chunks)} chunks)...")
    knowledge = extract_knowledge(all_chunks)
    print(f"  → {len(knowledge.entities)} entities, "
          f"{len(knowledge.concepts)} concepts, "
          f"{len(knowledge.relationships)} relationships")

    # Stage 3
    print("\n🔄 Stage 3: Diffing against wiki/index.md...")
    existing = load_index(WIKI_DIR / "index.md")
    for e in knowledge.entities:
        e.status = "UPDATE" if e.slug in existing.get("entities", {}) else "CREATE"
    for c in knowledge.concepts:
        c.status = "UPDATE" if c.slug in existing.get("concepts", {}) else "CREATE"

    ce = sum(1 for e in knowledge.entities if e.status == "CREATE")
    ue = sum(1 for e in knowledge.entities if e.status == "UPDATE")
    cc = sum(1 for c in knowledge.concepts if c.status == "CREATE")
    uc = sum(1 for c in knowledge.concepts if c.status == "UPDATE")
    print(f"  → Entities: {ce} create, {ue} update | Concepts: {cc} create, {uc} update")

    # Stage 4
    print("\n✍️  Stage 4: Entity files...")
    for entity in knowledge.entities:
        entity_chunks = [
            ch for ch in all_chunks
            if any(a.lower() in ch.content.lower() for a in ([entity.name] + entity.aliases)[:5])
        ] or all_chunks[:3]
        existing_content = load_file(WIKI_DIR / "entities" / f"{entity.slug}.md") if entity.status == "UPDATE" else None
        try:
            content = synthesize_entity(entity, entity_chunks[:6], existing_content, USE_WIKILINKS)
            write_file(WIKI_DIR / "entities" / f"{entity.slug}.md", content)
            print(f"  [{entity.status}] {entity.slug}")
        except Exception as e:
            print(f"  ⚠️  {entity.slug}: {e}")

    # Stage 5
    print("\n💡 Stage 5: Concept files...")
    for concept in knowledge.concepts:
        concept_chunks = [
            ch for ch in all_chunks
            if any(a.lower() in ch.content.lower() for a in ([concept.name] + concept.aliases)[:5])
        ] or all_chunks[:3]
        existing_content = load_file(WIKI_DIR / "concepts" / f"{concept.slug}.md") if concept.status == "UPDATE" else None
        try:
            content = synthesize_concept(concept, concept_chunks[:5], existing_content, USE_WIKILINKS)
            write_file(WIKI_DIR / "concepts" / f"{concept.slug}.md", content)
            print(f"  [{concept.status}] {concept.slug}")
        except Exception as e:
            print(f"  ⚠️  {concept.slug}: {e}")

    # Stage 6
    print("\n📋 Stage 6: Source summaries...")
    for source_file in unprocessed:
        source_chunks = [ch for ch in all_chunks if ch.source_file == str(source_file)]
        if not source_chunks:
            continue
        slug = source_file.stem.lower().replace(" ", "-").replace("_", "-")
        try:
            content = summarize_source(source_file, source_chunks, knowledge, USE_WIKILINKS)
            write_file(WIKI_DIR / "summaries" / f"{slug}.md", content)
            print(f"  → summaries/{slug}.md")
        except Exception as e:
            print(f"  ⚠️  {slug}: {e}")

    # Stage 7
    print("\n🗂️  Stage 7: Domain manifests...")
    domains: dict = {}
    for e in knowledge.entities:
        domains.setdefault(e.domain or "general", {"entities": [], "concepts": []})["entities"].append(e.slug)
    for c in knowledge.concepts:
        domains.setdefault(c.domain or "general", {"entities": [], "concepts": []})["concepts"].append(c.slug)

    for domain, contents in domains.items():
        dslug = domain.lower().replace(" ", "-")
        write_file(GRAPH_DIR / "domains" / f"{dslug}.md",
                   generate_domain_manifest(domain, contents["entities"], contents["concepts"]))
        print(f"  → graph/domains/{dslug}.md")

    _update_claude_domain_imports(domains)

    # Stage 8
    print("\n📑 Stage 8: Index, log, overview, anchors...")
    update_index(WIKI_DIR, knowledge)
    print("  → wiki/index.md")

    append_log(WIKI_DIR / "log.md", {
        "timestamp": datetime.now().isoformat(),
        "sources_processed": [str(f) for f in unprocessed],
        "entities_created": [e.slug for e in knowledge.entities if e.status == "CREATE"],
        "entities_updated": [e.slug for e in knowledge.entities if e.status == "UPDATE"],
        "concepts_created": [c.slug for c in knowledge.concepts if c.status == "CREATE"],
        "concepts_updated": [c.slug for c in knowledge.concepts if c.status == "UPDATE"],
    })
    print("  → wiki/log.md (appended)")

    overview_file = WIKI_DIR / "overview.md"
    if (ce + cc) > 10 or not overview_file.exists() or overview_file.stat().st_size < 100:
        try:
            write_file(overview_file, synthesize_overview(WIKI_DIR))
            print("  → wiki/overview.md (regenerated)")
        except Exception as e:
            print(f"  ⚠️  Overview: {e}")

    update_temporal_anchors(GRAPH_DIR / "interfaces" / "temporal.md", unprocessed)
    print("  → temporal anchors updated")

    for f in unprocessed:
        mark_processed(f)

    print(f"\n{'='*60}")
    print(f"✅ Done. Created {ce}E+{cc}C, updated {ue}E+{uc}C")
    print(f"   Run: python scripts/lint.py")
    print("=" * 60)


def _update_claude_domain_imports(domains: dict):
    claude_file = ROOT / "CLAUDE.md"
    if not claude_file.exists():
        return
    text = claude_file.read_text()
    marker = "## Domain Manifests"
    if marker not in text:
        return
    new_lines = []
    for domain in domains:
        line = f"@graph/domains/{domain.lower().replace(' ', '-')}.md"
        if line not in text:
            new_lines.append(line)
    if new_lines:
        idx = text.index(marker) + len(marker)
        nl = "\n"
        text = text[:idx] + f"\n{nl.join(new_lines)}" + text[idx:]
        claude_file.write_text(text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-process all sources")
    args = parser.parse_args()
    run_ingest(force=args.force)
