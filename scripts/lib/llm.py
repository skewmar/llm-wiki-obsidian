import os
import re
import json
import time
from pathlib import Path

import anthropic
from lib.schema import Entity, Concept, Relationship, ExtractedKnowledge

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-5"

ROOT = Path(__file__).parent.parent.parent
_ENTITY_SCHEMA = ""
_CONCEPT_SCHEMA = ""


def _load_schemas():
    global _ENTITY_SCHEMA, _CONCEPT_SCHEMA
    es = ROOT / "instructions" / "ENTITY_SCHEMA.md"
    cs = ROOT / "instructions" / "CONCEPT_SCHEMA.md"
    if es.exists():
        _ENTITY_SCHEMA = es.read_text()
    if cs.exists():
        _CONCEPT_SCHEMA = cs.read_text()


_load_schemas()


def _call_claude(model: str, system: str, user: str, max_tokens: int = 4096,
                 cache_system: bool = False) -> str:
    system_content = [{"type": "text", "text": system}]
    if cache_system:
        system_content[0]["cache_control"] = {"type": "ephemeral"}

    for attempt in range(4):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_content,
                messages=[{"role": "user", "content": user}],
            )
            return response.content[0].text
        except anthropic.RateLimitError:
            wait = 2 ** attempt * 5
            print(f"  ⏳ Rate limited — waiting {wait}s...")
            time.sleep(wait)
        except anthropic.APIStatusError as e:
            if e.status_code == 529:
                wait = 2 ** attempt * 10
                print(f"  ⏳ API overloaded — waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Max retries exceeded")


def extract_knowledge(chunks: list, batch_size: int = 10) -> ExtractedKnowledge:
    system = f"""You extract structured knowledge from personal communications and notes.

{_ENTITY_SCHEMA}

{_CONCEPT_SCHEMA}

Return ONLY valid JSON — no markdown fences, no explanation.

{{
  "entities": [
    {{"slug": "first-last", "name": "Full Name", "type": "person|company|project",
     "domain": "domain-slug", "aliases": ["alias"], "description": "one sentence"}}
  ],
  "concepts": [
    {{"slug": "concept-slug", "name": "Concept Name", "domain": "domain-slug",
     "aliases": ["alias"], "description": "one sentence"}}
  ],
  "relationships": [
    {{"from": "slug1", "to": "slug2", "type": "works_at|builds_on|contrasts_with|applies_to",
     "notes": ""}}
  ]
}}"""

    all_entities, all_concepts, all_relationships = {}, {}, []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i: i + batch_size]
        batch_text = "\n\n---\n\n".join(
            f"[{c.source_type} | {c.date or 'unknown date'}]\n{c.content}" for c in batch
        )
        try:
            raw = _call_claude(HAIKU, system, batch_text, cache_system=True)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = re.sub(r"```(?:json)?\n?", "", raw).strip().rstrip("`").strip()

            data = json.loads(raw)

            for e in data.get("entities", []):
                slug = e.get("slug", "").lower().replace(" ", "-")
                if slug and slug not in all_entities:
                    all_entities[slug] = Entity(
                        slug=slug,
                        name=e.get("name", slug),
                        entity_type=e.get("type", "person"),
                        domain=e.get("domain", "general"),
                        aliases=e.get("aliases", []),
                        description=e.get("description", ""),
                        source_files=[c.source_file for c in batch],
                    )

            for c in data.get("concepts", []):
                slug = c.get("slug", "").lower().replace(" ", "-")
                if slug and slug not in all_concepts:
                    all_concepts[slug] = Concept(
                        slug=slug,
                        name=c.get("name", slug),
                        domain=c.get("domain", "general"),
                        aliases=c.get("aliases", []),
                        description=c.get("description", ""),
                        source_files=[ch.source_file for ch in batch],
                    )

            for r in data.get("relationships", []):
                all_relationships.append(Relationship(
                    from_slug=r.get("from", ""),
                    to_slug=r.get("to", ""),
                    relationship_type=r.get("type", "relates_to"),
                    notes=r.get("notes", ""),
                ))

        except (json.JSONDecodeError, KeyError) as e:
            print(f"  ⚠️  Batch {i // batch_size + 1} extraction failed: {e}")

    return ExtractedKnowledge(
        entities=list(all_entities.values()),
        concepts=list(all_concepts.values()),
        relationships=all_relationships,
    )


def _link(name: str, path: str, use_wikilinks: bool) -> str:
    if use_wikilinks:
        return f"[[{Path(path).stem}]]"
    return f"[{name}]({path})"


def synthesize_entity(entity: Entity, chunks: list, existing: str = None,
                      use_wikilinks: bool = False) -> str:
    link_note = ("Use [[Slug]] wikilinks for all internal references."
                 if use_wikilinks else
                 "Use [Name](../entities/slug.md) markdown links for internal references.")
    action = "Update" if existing else "Create"
    existing_block = f"\n\nEXISTING (preserve + extend, never delete):\n{existing}" if existing else ""

    system = f"""You maintain a personal knowledge base wiki. {link_note}

Entity file format:
---
type: entity
subtype: {entity.entity_type}
domain: {entity.domain}
slug: {entity.slug}
last_updated: YYYY-MM-DD
sources: []
status: active
---

# {entity.name}
> One sentence, most specific fact first.

## Aliases
[name variations]

## Current Status
[current] role/state as of [YYYY-MM]

## Key Facts
- Fact [as of YYYY-MM]

## Relationships
| Relationship | Target | Notes |
|---|---|---|

## How Thinking Has Evolved
[early thinking] → [evolved to] (if applicable)

## Open Questions
- Open question this entity raises

## Answers Questions
- Natural language questions this file answers

## Sources
| File | Date | Role |
|---|---|---|

Rules: [as of YYYY-MM] on all facts. [inferred] for uncertain claims. Never fabricate. On update: add [evolved to], preserve all existing content."""

    chunks_text = "\n\n---\n\n".join(
        f"[{c.source_type} | {c.date or 'unknown'}]\n{c.content}" for c in chunks[:6]
    )
    user = (f"{action} entity for: {entity.name}\n"
            f"Description: {entity.description}\n"
            f"Aliases: {', '.join(entity.aliases)}"
            f"{existing_block}\n\nSource material:\n{chunks_text}")

    return _call_claude(SONNET, system, user, max_tokens=2000)


def synthesize_concept(concept: Concept, chunks: list, existing: str = None,
                       use_wikilinks: bool = False) -> str:
    link_note = ("Use [[Slug]] wikilinks." if use_wikilinks
                 else "Use [Name](../concepts/slug.md) markdown links.")
    action = "Update" if existing else "Create"
    existing_block = f"\n\nEXISTING:\n{existing}" if existing else ""

    system = f"""You maintain a personal knowledge base wiki. {link_note}

Concept file format:
---
type: concept
domain: {concept.domain}
slug: {concept.slug}
last_updated: YYYY-MM-DD
maturity: seed
sources: []
---

# {concept.name}
> Core claim in one sentence.

## Aliases
[all names]

## The Argument
[Full description. Mark evolution: [early thinking] → [evolved to]]

## Where This Shows Up
- [entity/context link]

## Relationships
| Type | Target | Notes |
|---|---|---|

## Open Questions
- Unresolved question

## Answers Questions
- Questions this concept file answers

## Sources
| File | Date | Role |
|---|---|---|

Same rules as entity files."""

    chunks_text = "\n\n---\n\n".join(
        f"[{c.source_type} | {c.date or 'unknown'}]\n{c.content}" for c in chunks[:5]
    )
    user = (f"{action} concept for: {concept.name}\n"
            f"Description: {concept.description}"
            f"{existing_block}\n\nSource material:\n{chunks_text}")

    return _call_claude(SONNET, system, user, max_tokens=1500)


def summarize_source(source_file: Path, chunks: list, knowledge,
                     use_wikilinks: bool = False) -> str:
    link_note = "Use [[Slug]] wikilinks." if use_wikilinks else "Use [Name](../entities/slug.md) links."
    entity_names = [e.name for e in knowledge.entities][:10]
    concept_names = [c.name for c in knowledge.concepts][:5]

    system = f"""You summarize source documents for a personal knowledge base. {link_note}

Format:
---
type: summary
source_file: {source_file.name}
source_type: {chunks[0].source_type if chunks else 'unknown'}
date_range: [earliest–latest]
entities_mentioned: {entity_names}
concepts_mentioned: {concept_names}
last_updated: YYYY-MM-DD
---

# Summary: {source_file.stem}
> One sentence: what this source is and contains.

## What This Source Contains
[2–3 paragraphs]

## Key Facts Extracted
- Fact [as of YYYY-MM]

## Entities Mentioned
[list with links]

## Concepts Discussed
[list with links]

## Questions This Source Answers
- [list]"""

    content = "\n\n---\n\n".join(c.content for c in chunks[:10])
    return _call_claude(SONNET, system, f"Summarize:\n\n{content}", max_tokens=1500)


def synthesize_overview(wiki_dir: Path) -> str:
    index_file = wiki_dir / "index.md"
    index_text = index_file.read_text()[:3000] if index_file.exists() else ""

    system = """Synthesize a high-level overview of a personal knowledge base.
3–5 paragraphs covering: who this belongs to, main themes/domains, most important
entities and concepts, key connections, time range and source types. Clean markdown, no headers."""

    return _call_claude(SONNET, system, f"Create overview from:\n\n{index_text}", max_tokens=800)


def generate_domain_manifest(domain: str, entity_slugs: list, concept_slugs: list) -> str:
    entities = "\n".join(f"- {s}" for s in entity_slugs) or "- (none yet)"
    concepts = "\n".join(f"- {s}" for s in concept_slugs) or "- (none yet)"
    title = domain.replace("-", " ").title()
    return f"""# Domain: {title}

## Entities
{entities}

## Concepts
{concepts}

## Routing Hint
Questions about {title} → load entity/concept files above.
Check wiki/index.md for full paths.
"""
