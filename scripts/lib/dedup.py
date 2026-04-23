import hashlib
import json
from pathlib import Path
from datetime import datetime

REGISTRY_FILE = Path(".processed_hashes")
RAW_EXTENSIONS = {".txt", ".mbox", ".md"}


def get_content_hash(file_path: Path) -> str:
    with open(file_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def load_registry() -> dict:
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text())
    return {}


def save_registry(registry: dict):
    REGISTRY_FILE.write_text(json.dumps(registry, indent=2))


def get_unprocessed_files(raw_dir: Path, force: bool = False) -> list:
    registry = {} if force else load_registry()
    unprocessed = []

    for f in raw_dir.rglob("*"):
        if not f.is_file():
            continue
        if "fetched" in f.parent.name:
            continue
        if f.suffix.lower() not in RAW_EXTENSIONS:
            continue
        if f.name.startswith(".") or f.name.endswith(".gitkeep"):
            continue
        content_hash = get_content_hash(f)
        if content_hash not in registry:
            unprocessed.append(f)

    fetched_dir = raw_dir / "fetched"
    if fetched_dir.exists():
        for f in fetched_dir.glob("*.txt"):
            if f.name.startswith("."):
                continue
            content_hash = get_content_hash(f)
            if content_hash not in registry:
                unprocessed.append(f)

    return unprocessed


def mark_processed(file_path: Path):
    registry = load_registry()
    content_hash = get_content_hash(file_path)
    registry[content_hash] = {
        "file": str(file_path),
        "processed_at": datetime.now().isoformat(),
    }
    save_registry(registry)
