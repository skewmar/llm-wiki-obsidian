# Question Router

## Decision Logic
1. Is a specific person named? → load `wiki/entities/[slug].md` first
2. Is a specific company/project named? → load `wiki/entities/[slug].md` first
3. Is the question conceptual ("what is X")? → load `wiki/concepts/[slug].md` first
4. Is the question about evolution or time? → apply `temporal.md` before answering
5. Spans multiple entities? → load domain manifest first, then relevant entity files
6. About my own history or work? → load `wiki/overview.md` first
7. Entity not in `wiki/index.md`? → answer: "not yet ingested — run ingest.py"

## Routing Table
| Question signals | Load first |
|---|---|
| Named person | `wiki/entities/[slug].md` |
| Named company or org | `wiki/entities/[slug].md` |
| Concept, framework, thesis | `wiki/concepts/[slug].md` |
| Cross-domain, compare, relate | domain manifests → `wiki/comparisons/` |
| My work, my history | `wiki/overview.md` |
| Temporal, evolved, changed | apply `temporal.md` |
| Intersection, connection, both | apply `intersections.md` |

## Entity Slug Rules
- People: `firstname-lastname` (e.g. `jane-doe`)
- Companies: `company-name` lowercased, hyphens for spaces
- All slugs listed in `wiki/index.md`

## Never
- Load all entity files at once
- Answer from `raw/` files directly
- Guess about entities not in `wiki/index.md`
