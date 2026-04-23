# Intersections — Cross-Domain Connection Routing

## Purpose
Surface non-obvious connections between entities and concepts across domains.
Use when a question seeks synthesis, comparison, or unexpected links.

## When to Apply This File
- Question contains: "connect", "relate", "intersection", "both", "across", "how does X relate to Y"
- Question asks how two named entities or concepts interact
- Question asks for novel insight or synthesis

## How to Find Intersections
1. Load `wiki/index.md` — scan for entities/concepts that share domain tags or sources
2. Check `wiki/comparisons/` — does a synthesis page already exist?
3. If not: load both entity/concept files, identify shared themes
4. File the synthesis back as a new page in `wiki/comparisons/`

## Intersection Signals
- Two entities both linked from the same concept page → related
- Two concepts appear in the same source summary → co-occur
- Entity A has [[Entity B]] in its Relationships table → explicit link
- Two entities with no direct link but 3+ shared sources → comparison candidate

## Lint-Generated Candidates
(Updated by `python scripts/lint.py` — pairs that co-occur 3+ times, no comparison page yet)
- (none yet — run lint.py after sources are ingested)
