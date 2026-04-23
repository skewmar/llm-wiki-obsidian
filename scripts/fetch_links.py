#!/usr/bin/env python3
"""
fetch_links.py — Extract URLs from raw/ sources and save as text to raw/fetched/.

Usage:
    python scripts/fetch_links.py
"""

import re
import time
import hashlib
import requests
import html2text
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "raw"
FETCHED_DIR = RAW_DIR / "fetched"
REGISTRY_FILE = FETCHED_DIR / "registry.md"
ERROR_LOG = FETCHED_DIR / "fetch_errors.log"

SKIP_DOMAINS = {
    "google.com", "gmail.com", "accounts.google.com",
    "calendar.google.com", "mail.google.com",
    "linkedin.com", "twitter.com", "x.com",
    "facebook.com", "instagram.com", "youtube.com",
}
SKIP_PATTERNS = [
    r"unsubscribe", r"optout", r"opt-out",
    r"\.(jpg|jpeg|png|gif|pdf|zip|mp4|mov)$",
    r"^mailto:", r"^tel:",
]
SHORTENER_DOMAINS = {"t.co", "bit.ly", "lnkd.in", "tinyurl.com", "ow.ly", "goo.gl"}
URL_RE = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def _should_skip(url: str) -> bool:
    try:
        domain = urlparse(url).netloc.lower().replace("www.", "")
        if any(s in domain for s in SKIP_DOMAINS):
            return True
        return any(re.search(p, url, re.IGNORECASE) for p in SKIP_PATTERNS)
    except Exception:
        return True


def _expand_shortener(url: str, session: requests.Session) -> str:
    try:
        domain = urlparse(url).netloc.lower().replace("www.", "")
        if domain in SHORTENER_DOMAINS:
            r = session.head(url, allow_redirects=True, timeout=10)
            return r.url
    except Exception:
        pass
    return url


def _load_fetched_urls() -> set:
    if not REGISTRY_FILE.exists():
        return set()
    fetched = set()
    for line in REGISTRY_FILE.read_text().split("\n"):
        if line.startswith("| ") and not line.startswith("| URL"):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 2 and parts[1]:
                fetched.add(parts[1])
    return fetched


def _save_registry_entry(url: str, source: str, status: str):
    FETCHED_DIR.mkdir(parents=True, exist_ok=True)
    if not REGISTRY_FILE.exists():
        REGISTRY_FILE.write_text(
            "# URL Registry\n\n| URL | Hash | Source | Fetched | Status |\n|---|---|---|---|---|\n"
        )
    today = datetime.now().strftime("%Y-%m-%d")
    with open(REGISTRY_FILE, "a") as f:
        f.write(f"| {url[:100]} | {_url_hash(url)} | {source} | {today} | {status} |\n")


def _fetch_and_save(url: str, source: str, session: requests.Session) -> bool:
    output = FETCHED_DIR / f"{_url_hash(url)}.txt"
    try:
        r = session.get(url, timeout=15,
                        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
        if r.status_code >= 400:
            _save_registry_entry(url, source, f"error-{r.status_code}")
            with open(ERROR_LOG, "a") as f:
                f.write(f"{datetime.now().isoformat()} | {r.status_code} | {url}\n")
            return False

        h = html2text.HTML2Text()
        h.ignore_links = True
        h.ignore_images = True
        h.body_width = 0
        text = h.handle(r.text)

        header = f"# Source: {url}\n# Fetched: {datetime.now().isoformat()}\n# From: {source}\n\n"
        output.write_text(header + text)
        _save_registry_entry(url, source, "ok")
        return True

    except requests.RequestException as e:
        _save_registry_entry(url, source, "error")
        with open(ERROR_LOG, "a") as f:
            f.write(f"{datetime.now().isoformat()} | error | {url} | {str(e)[:100]}\n")
        return False


def main():
    FETCHED_DIR.mkdir(parents=True, exist_ok=True)
    print("🔗 Extracting URLs from raw/ sources...")

    all_urls: dict = {}
    for source_dir in [RAW_DIR / "emails", RAW_DIR / "whatsapp", RAW_DIR / "notes"]:
        if not source_dir.exists():
            continue
        for f in source_dir.rglob("*"):
            if f.is_file() and f.suffix in {".txt", ".mbox", ".md"}:
                try:
                    text = f.read_text(encoding="utf-8", errors="replace")
                    for url in URL_RE.findall(text):
                        url = url.rstrip(".,;:)\"'")
                        if url not in all_urls:
                            all_urls[url] = f.name
                except Exception:
                    pass

    print(f"  → {len(all_urls)} unique URLs found")
    all_urls = {u: s for u, s in all_urls.items() if not _should_skip(u)}
    print(f"  → {len(all_urls)} after filtering noise")

    already_fetched = _load_fetched_urls()
    to_fetch = {u: s for u, s in all_urls.items() if u not in already_fetched}
    print(f"  → {len(to_fetch)} new URLs to fetch")

    if not to_fetch:
        print("✅ All URLs already fetched.")
        return

    session = requests.Session()
    expanded = {}
    for url, src in to_fetch.items():
        expanded[_expand_shortener(url, session)] = src

    success = 0
    for i, (url, src) in enumerate(expanded.items()):
        print(f"  [{i+1}/{len(expanded)}] {url[:80]}...")
        if _fetch_and_save(url, src, session):
            success += 1
        time.sleep(1)

    print(f"\n✅ Fetched {success}/{len(expanded)} URLs → raw/fetched/")


if __name__ == "__main__":
    main()
