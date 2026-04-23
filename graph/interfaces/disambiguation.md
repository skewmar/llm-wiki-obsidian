# Disambiguation Rules

## When Two Things Seem Identical
1. Check `wiki/index.md` — are there two separate files, or just one?
2. If two files exist, load both and check their Aliases sections
3. Use the file whose description best matches the question context
4. If still ambiguous, ask the user which they mean

## Common Disambiguation Patterns

**Person vs Company with same name**
→ Check `subtype:` in frontmatter — `person` vs `company`

**Concept vs Entity**
→ Concepts explain ideas/frameworks. Entities are specific named things.
→ "What is X?" → concept. "Who is X?" or "What does X do?" → entity.

**Same slug, different domain**
→ Load both files, present context from each, clarify which applies

**Outdated vs current version of an idea**
→ Apply `temporal.md` — look for `[evolved to]` markers in the concept file

## If Truly Ambiguous
State: "I found multiple matches for [name]. Did you mean:
- [Option A] ([[entity-slug]]): [one-line description]
- [Option B] ([[concept-slug]]): [one-line description]"
