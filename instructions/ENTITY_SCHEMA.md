# Entity File Schema

Entities are specific named things: people, companies, projects.
One file per entity in wiki/entities/[slug].md

## Frontmatter
```yaml
---
type: entity
subtype: person | company | project
domain: domain-slug
slug: entity-slug
last_updated: YYYY-MM-DD
sources: [list of source filenames]
status: active | archived
---
```

## Body Sections (required)

```markdown
# Entity Name
> One-sentence description. Most specific, surprising fact first — not background.

## Aliases
All name variations, abbreviations, nicknames — one per line

## Current Status
[current] role/state as of [YYYY-MM]

## Key Facts
- Fact [as of YYYY-MM]
- Another fact [inferred]

## Relationships
| Relationship | Target | Notes |
|---|---|---|
| works at | [[Company]] | [as of YYYY-MM] |
| collaborates with | [[Person]] | context |

## How Thinking Has Evolved
[early thinking] initial position
[evolved to] updated position (omit this section if no evolution observed)

## Open Questions
- Question this entity raises that isn't yet answered in the wiki

## Answers Questions
- Natural language questions this file answers

## Sources
| File | Date | Role |
|---|---|---|
| [[summary-slug]] | YYYY-MM | primary |
```

## Temporal Marker Rules
- All facts in Key Facts must have [as of YYYY-MM] or [current] or [inferred]
- Position changes must use [early thinking] → [evolved to] pattern
- Never delete old content — mark it [archived] or [evolved to] instead
- [unconfirmed] for anything heard but not verified in source material

## Obsidian Note
Use [[wikilinks]] everywhere — NOT markdown links. Only [[wikilinks]] create
visible edges in Obsidian's graph view.
