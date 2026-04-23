# Concept File Schema

Concepts are recurring ideas, frameworks, arguments, or theses.
One file per concept in wiki/concepts/[slug].md

## Frontmatter
```yaml
---
type: concept
domain: domain-slug
slug: concept-slug
last_updated: YYYY-MM-DD
maturity: seed | developing | stable
sources: [list of source filenames]
---
```

## Body Sections (required)

```markdown
# Concept Name
> Core claim in one sentence.

## Aliases
All names this concept goes by

## The Argument
Full description of the concept, framework, or idea.
Mark evolution explicitly:
[early thinking] original framing
[evolved to] current framing

## Where This Shows Up
- [[Entity or context where this concept applies]]
- [[Another entity]]

## Relationships
| Type | Target | Notes |
|---|---|---|
| builds on | [[Other Concept]] | why |
| contrasts with | [[Other Concept]] | how they differ |
| applies to | [[Entity]] | in what context |

## Open Questions
- Unresolved question this concept raises
- What would change this position

## Answers Questions
- Questions this concept file answers

## Sources
| File | Date | Role |
|---|---|---|
| [[summary-slug]] | YYYY-MM | introduces |
| [[summary-slug]] | YYYY-MM | deepens |
```

## Maturity Levels
- `seed` — first appearance, thin description
- `developing` — multiple sources, argument forming
- `stable` — well-articulated, sourced, evolution tracked

## Obsidian Note
Use [[wikilinks]] everywhere — NOT markdown links. Only [[wikilinks]] create
visible edges in Obsidian's graph view.
