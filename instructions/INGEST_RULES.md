# Ingest Rules

## What Gets Ingested
- Files in raw/emails/ with extension .txt or .mbox
- Files in raw/whatsapp/ named _chat.txt or similar WhatsApp exports
- Files in raw/notes/ with extension .txt or .md
- Files in raw/fetched/ with extension .txt (output of fetch_links.py)

## What Gets Skipped
- Files already in .processed_hashes registry (content-hash dedup)
- .gitkeep, .DS_Store, hidden files
- Files smaller than 30 characters of content
- registry.md and fetch_errors.log in raw/fetched/

## Deduplication
Content-hash based (MD5). The same file re-added with a different name will be skipped.
Use --force flag to re-process everything regardless of hash registry.

## Email Parsing
- .mbox files: parsed via Python mailbox library, one chunk per message
- .txt files: split by "--- Original Message ---", "On ... wrote:", and similar delimiters
- Quoted/forwarded history is preserved in each chunk for context
- One chunk = one email or reply, capped at 4000 characters

## WhatsApp Parsing
- Format: "DD/MM/YYYY, HH:MM - Sender: Message"
- System messages filtered (encryption notice, added/removed, etc.)
- Grouped by calendar day into chunks (one chunk per day)
- Supports both 12h and 24h time formats

## Notes Parsing
- Split by markdown headings (##, ###) or --- dividers
- Each section becomes one chunk
- Falls back to single chunk if no dividers found

## URL Fetching (fetch_links.py, run separately)
- Extracts all https:// URLs from email and WhatsApp files
- Skips: social media, calendar, unsubscribe links, image files
- Expands shorteners (t.co, bit.ly, lnkd.in)
- Saves HTML→text to raw/fetched/[md5hash].txt
- Registry at raw/fetched/registry.md tracks what was fetched

## Batch Size
- Extraction (Stage 2): 10 chunks per Claude Haiku call
- Synthesis (Stages 4-6): up to 6-8 chunks per Claude Sonnet call
- Prompt caching enabled on schema system prompts for cost efficiency

## Update Behavior
- CREATE: new entity/concept file written from scratch
- UPDATE: existing content loaded, new content merged, [evolved to] markers added
- Existing content is never deleted, only extended
- wiki/log.md is append-only and never truncated
