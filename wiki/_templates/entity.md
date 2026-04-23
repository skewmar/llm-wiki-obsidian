---
type: entity
subtype: person
domain: general
slug: <% tp.file.title %>
created: <% tp.date.now("YYYY-MM-DD") %>
last_updated: <% tp.date.now("YYYY-MM-DD") %>
sources: []
status: active
---

# <% tp.file.title %>
> One-sentence description. Most specific fact first, not background.

## Aliases
List all name variations, abbreviations, nicknames — one per line

## Current Status
[current] role/state as of [<% tp.date.now("YYYY-MM") %>]

## Key Facts
- Fact one [as of <% tp.date.now("YYYY-MM") %>]
- Fact two [inferred]

## Relationships
| Relationship | Target | Notes |
|---|---|---|
| works at | [[Company Name]] | [as of <% tp.date.now("YYYY-MM") %>] |
| collaborates with | [[Person Name]] | context |

## How Thinking Has Evolved
[early thinking] description → [evolved to] updated position

## Open Questions
- Question this entity raises that isn't yet answered in the wiki

## Answers Questions
- Natural language questions this file answers

## Sources
| File | Date | Role |
|---|---|---|
| [[summary-slug]] | <% tp.date.now("YYYY-MM") %> | primary |
