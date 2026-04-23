#!/usr/bin/env python3
"""
lint.py — Health check the wiki + find intersectional opportunities.

Obsidian version: wikilink checking is ON by default.

Usage:
    python scripts/lint.py               # Health check (wikilinks mode)
    python scripts/lint.py --generate    # Also draft comparison pages
    python scripts/lint.py --no-wikilinks  # Use markdown link checking instead
"""

import re
import sys
import argparse
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv()

ROOT = Path(__file__).parent.parent
WIKI_DIR = ROOT / "wiki"
GRAPH_DIR = ROOT / "graph"
RAW_DIR = ROOT / "raw"


def check_orphans(wiki_dir: Path) -> list:
    issues = []
    index_file = wiki_dir / "index.md"
    if not index_file.exists():
        return [("ERROR", "wiki/index.md missing — run ingest.py first")]
    index_text = index_file.read_text()
    for sub in ["entities", "concepts", "summaries"]:
        d = wiki_dir / sub
        if not d.exists():
            continue
        for f in d.glob("*.md"):
            if f.name.startswith("_"):
                continue
            if f.stem not in index_text:
                issues.append(("ORPHAN", f"wiki/{sub}/{f.name} not in index.md"))
    return issues


def check_broken_links(wiki_dir: Path, wikilinks: bool) -> list:
    issues = []
    all_stems = {f.stem for f in wiki_dir.rglob("*.md") if not f.name.startswith("_")}
    pat = re.compile(r"\[\[([^\]|]+)") if wikilinks else re.compile(r"\[[^\]]+\]\(([^)]+\.md)\)")

    for f in wiki_dir.rglob("*.md"):
        if f.name.startswith("_"):
            continue
        for m in pat.finditer(f.read_text()):
            target = m.group(1).strip()
            if wikilinks:
                if target not in all_stems and target.lower() not in all_stems:
                    issues.append(("BROKEN_LINK", f"{f.relative_to(ROOT)}: [[{target}]] not found"))
            else:
                if target.startswith("http") or target.startswith("#"):
                    continue
                resolved = (f.parent / target).resolve()
                if not resolved.exists():
                    issues.append(("BROKEN_LINK", f"{f.relative_to(ROOT)}: [{target}] not found"))
    return issues


def check_stale_summaries(wiki_dir: Path, raw_dir: Path) -> list:
    issues = []
    summaries = wiki_dir / "summaries"
    if not summaries.exists():
        return issues
    raw_stems = {f.stem for f in raw_dir.rglob("*") if f.is_file()}
    for f in summaries.glob("*.md"):
        if f.name.startswith("_"):
            continue
        source = ""
        for line in f.read_text().split("\n"):
            if "source_file:" in line:
                source = line.split(":", 1)[1].strip()
                break
        if source and Path(source).stem not in raw_stems:
            issues.append(("STALE", f"wiki/summaries/{f.name}: source '{source}' missing from raw/"))
    return issues


def check_temporal_markers(wiki_dir: Path) -> list:
    issues = []
    markers = ["[as of", "[current]", "[early thinking]", "[evolved to]", "[inferred]", "[unconfirmed]"]
    for sub in ["entities", "concepts"]:
        d = wiki_dir / sub
        if not d.exists():
            continue
        for f in d.glob("*.md"):
            if f.name.startswith("_"):
                continue
            text = f.read_text()
            if "## Key Facts" in text:
                facts = text.split("## Key Facts")[1].split("##")[0]
                if facts.strip() and not any(m in facts for m in markers):
                    issues.append(("MISSING_TEMPORAL", f"wiki/{sub}/{f.name}: Key Facts lacks temporal markers"))
    return issues


def find_intersections(wiki_dir: Path, min_co: int = 3) -> list:
    summaries = wiki_dir / "summaries"
    comparisons = wiki_dir / "comparisons"
    if not summaries.exists():
        return []

    entity_sources: dict = defaultdict(set)
    wl_pat = re.compile(r"\[\[([^\]|]+)")
    ml_pat = re.compile(r"\[([^\]]+)\]\(\.\./entities/([^)]+)\.md\)")

    for f in summaries.glob("*.md"):
        if f.name.startswith("_"):
            continue
        text = f.read_text()
        mentioned = set()
        for line in text.split("\n"):
            if "entities_mentioned:" in line:
                for n in re.findall(r"'([^']+)'|\"([^\"]+)\"", line):
                    slug = (n[0] or n[1]).lower().replace(" ", "-")
                    mentioned.add(slug)
        for m in wl_pat.finditer(text):
            mentioned.add(m.group(1).strip().lower())
        for m in ml_pat.finditer(text):
            mentioned.add(m.group(2))
        for slug in mentioned:
            entity_sources[slug].add(f.stem)

    existing = {f.stem for f in comparisons.glob("*.md")} if comparisons.exists() else set()
    candidates = []
    slugs = list(entity_sources.keys())

    for i in range(len(slugs)):
        for j in range(i + 1, len(slugs)):
            shared = entity_sources[slugs[i]] & entity_sources[slugs[j]]
            if len(shared) >= min_co:
                a, b = slugs[i], slugs[j]
                if f"{a}-x-{b}" not in existing and f"{b}-x-{a}" not in existing:
                    candidates.append({"a": a, "b": b, "shared": sorted(shared), "n": len(shared)})

    return sorted(candidates, key=lambda x: x["n"], reverse=True)[:20]


def update_intersections_file(candidates: list):
    ifile = GRAPH_DIR / "interfaces" / "intersections.md"
    if not ifile.exists():
        return
    text = ifile.read_text()
    if not candidates:
        block = "- (none yet — run after more sources are ingested)"
    else:
        block = "\n".join(
            f"- **{c['a']}** × **{c['b']}** — {c['n']} shared sources: {', '.join(c['shared'][:3])}"
            for c in candidates
        )
    marker = "## Lint-Generated Candidates"
    if marker in text:
        text = text[: text.index(marker)] + f"{marker}\n{block}\n"
    else:
        text += f"\n{marker}\n{block}\n"
    ifile.write_text(text)


def generate_comparison(a: str, b: str, shared: list, wikilinks: bool) -> str:
    try:
        from lib.llm import _call_claude, SONNET
        la = f"[[{a}]]" if wikilinks else f"[{a}](../entities/{a}.md)"
        lb = f"[[{b}]]" if wikilinks else f"[{b}](../entities/{b}.md)"
        system = f"Create a synthesis/comparison wiki page. Use {'[[wikilinks]]' if wikilinks else 'markdown links'}."
        user = f"""Create comparison page: {a} × {b}
Co-occur in: {', '.join(shared)}

---
type: comparison
entities: [{a}, {b}]
shared_sources: {shared}
---

# {a.replace('-',' ').title()} × {b.replace('-',' ').title()}
> One-sentence synthesis of the connection.

## The Connection
[what these two share or how they interact]

## Where They Diverge
[key differences]

## Intersectional Insight
[non-obvious synthesis from looking at both together]

## Related
- {la}
- {lb}"""
        return _call_claude(SONNET, system, user, max_tokens=1000)
    except Exception as e:
        return f"# {a} × {b}\n\nPopulate manually.\n\n*Generation failed: {e}*"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true", help="Draft top comparison pages")
    parser.add_argument("--no-wikilinks", action="store_true",
                        help="Check markdown links instead of [[wikilinks]] (non-Obsidian mode)")
    args = parser.parse_args()

    # Obsidian version defaults to wikilinks
    use_wikilinks = not args.no_wikilinks

    print("🔍 Wiki health check\n")
    all_issues = []

    checks = [
        ("Orphaned files", check_orphans(WIKI_DIR)),
        ("Broken links", check_broken_links(WIKI_DIR, use_wikilinks)),
        ("Stale summaries", check_stale_summaries(WIKI_DIR, RAW_DIR)),
        ("Missing temporal markers", check_temporal_markers(WIKI_DIR)),
    ]
    for label, issues in checks:
        print(f"{label}: {len(issues)} issue(s)")
        all_issues.extend(issues)

    print(f"\nFinding intersections...")
    candidates = find_intersections(WIKI_DIR)
    print(f"  → {len(candidates)} candidate(s)")
    update_intersections_file(candidates)
    print("  → graph/interfaces/intersections.md updated")

    print("\n" + "=" * 50)
    if all_issues:
        print(f"\n⚠️  {len(all_issues)} issue(s):\n")
        icons = {"ORPHAN": "📄", "BROKEN_LINK": "🔗", "STALE": "⏰",
                 "MISSING_TEMPORAL": "🕐", "ERROR": "❌"}
        for itype, msg in all_issues:
            print(f"  {icons.get(itype,'•')} [{itype}] {msg}")
    else:
        print("\n✅ No issues found.")

    if candidates:
        print(f"\n💡 Top intersection candidates:\n")
        for c in candidates[:5]:
            print(f"  • {c['a']} × {c['b']} ({c['n']} shared sources)")

        if args.generate:
            comp_dir = WIKI_DIR / "comparisons"
            comp_dir.mkdir(exist_ok=True)
            print("\n✍️  Generating comparison pages...")
            for c in candidates[:3]:
                slug = f"{c['a']}-x-{c['b']}"
                out = comp_dir / f"{slug}.md"
                out.write_text(generate_comparison(c["a"], c["b"], c["shared"], use_wikilinks))
                print(f"  → wiki/comparisons/{slug}.md")


if __name__ == "__main__":
    main()
