# Temporal Reasoning Rules

## Markers Used in wiki/ Files
| Marker | Meaning |
|---|---|
| `[as of YYYY-MM]` | Confirmed as of that month — may have changed since |
| `[early thinking]` | Initial position, likely superseded — look for [evolved to] |
| `[evolved to]` | Successor position — supersedes [early thinking] in same file |
| `[current]` | Most recent confirmed state in this knowledge base |
| `[inferred]` | Derived from context — lower confidence, do not assert as fact |
| `[unconfirmed]` | Heard but not verified — never cite as fact |
| `[archived]` | No longer active — kept for historical context |

## Rules
- "now / today / current" → find `[current]` or most recent `[as of YYYY-MM]`
- "how did X evolve / change" → trace `[early thinking]` → `[evolved to]` chain
- "recently / lately" → within 6 months of latest entry in `wiki/log.md`
- "originally / at first / early" → find `[early thinking]` markers
- Conflicting facts across time → present both with timestamps, do not merge

## Time Anchors (updated by ingest.py on each run)
- Earliest source: TBD
- Most recent source: TBD
- Last ingest run: TBD
