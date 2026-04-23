#!/usr/bin/env python3
"""
watch.py — Monitor raw/ for new files and auto-trigger ingest.

Usage:
    python scripts/watch.py              # Watch and ingest on new files
    python scripts/watch.py --fetch      # Also run fetch_links.py first
"""

import sys
import time
import subprocess
import argparse
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "raw"
DEBOUNCE = 30  # seconds to wait after last file event before triggering
WATCHED_EXT = {".txt", ".mbox", ".md"}

_pending: set = set()
_last_event: float = 0


class Handler(FileSystemEventHandler):
    def on_created(self, event):
        self._handle(event)

    def on_modified(self, event):
        self._handle(event)

    def _handle(self, event):
        global _last_event
        if event.is_directory:
            return
        p = Path(event.src_path)
        if "fetched" in str(p) or p.name.startswith(".") or p.suffix.lower() not in WATCHED_EXT:
            return
        _pending.add(str(p))
        _last_event = time.time()
        print(f"📥 New file detected: {p.name}")


def run_pipeline(fetch_first: bool):
    if fetch_first:
        print("\n🔗 Running fetch_links.py...")
        subprocess.run([sys.executable, str(ROOT / "scripts" / "fetch_links.py")], cwd=ROOT)
    print("\n🔄 Running ingest.py...")
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "ingest.py")], cwd=ROOT)
    status = "✅ Done" if result.returncode == 0 else "⚠️  Finished with errors"
    print(f"{status}\n")
    _pending.clear()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true", help="Run fetch_links before ingest")
    args = parser.parse_args()

    print(f"👀 Watching {RAW_DIR} (debounce: {DEBOUNCE}s) — Ctrl+C to stop\n")
    observer = Observer()
    observer.schedule(Handler(), str(RAW_DIR), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(5)
            if _pending and (time.time() - _last_event) >= DEBOUNCE:
                print(f"\n⚡ Triggering pipeline for {len(_pending)} file(s)...")
                run_pipeline(fetch_first=args.fetch)
    except KeyboardInterrupt:
        print("\n👋 Watcher stopped.")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
