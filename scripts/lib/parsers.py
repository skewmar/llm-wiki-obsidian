import re
import hashlib
import mailbox
from pathlib import Path
from lib.schema import Chunk


def _make_id(source: str, i: int) -> str:
    return hashlib.md5(f"{source}:{i}".encode()).hexdigest()[:8]


def _extract_date(text: str) -> str:
    for pattern in [r"Date:\s*(.+?)(?:\n|$)", r"Sent:\s*(.+?)(?:\n|$)",
                    r"On\s+(\w+ \d+, \d{4})", r"(\d{1,2}/\d{1,2}/\d{2,4})"]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:50]
    return ""


def _extract_participants(text: str) -> list:
    participants = []
    for field in ["From:", "To:", "Cc:"]:
        m = re.search(rf"{field}\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
        if m:
            participants.extend(re.findall(r"[\w.+-]+@[\w.-]+", m.group(1)))
    return list(set(participants))


def parse_email_thread(file_path: Path) -> list:
    chunks = []
    text = file_path.read_text(encoding="utf-8", errors="replace")

    if file_path.suffix == ".mbox" or text.startswith("From "):
        try:
            mbox = mailbox.mbox(str(file_path))
            messages = list(mbox)
            if messages:
                return _parse_mbox_messages(messages, file_path)
        except Exception:
            pass

    parts = _split_text_email_thread(text)
    for i, part in enumerate(parts):
        if len(part.strip()) < 50:
            continue
        chunks.append(Chunk(
            chunk_id=_make_id(str(file_path), i),
            source_file=str(file_path),
            source_type="email",
            date=_extract_date(part),
            participants=_extract_participants(part),
            content=part.strip()[:4000],
        ))
    return chunks


def _parse_mbox_messages(messages, file_path: Path) -> list:
    chunks = []
    for i, msg in enumerate(messages):
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode("utf-8", errors="replace")
                    break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="replace")

        if len(body.strip()) < 30:
            continue

        content = (f"From: {msg.get('From','')}\n"
                   f"Date: {msg.get('Date','')}\n"
                   f"Subject: {msg.get('Subject','')}\n\n{body}")
        chunks.append(Chunk(
            chunk_id=_make_id(str(file_path), i),
            source_file=str(file_path),
            source_type="email",
            date=msg.get("Date", ""),
            participants=[msg.get("From", "")],
            content=content[:4000],
        ))
    return chunks


def _split_text_email_thread(text: str) -> list:
    separators = [
        r"-{3,}.*?Original Message.*?-{3,}",
        r"-{3,}.*?Forwarded message.*?-{3,}",
        r"On .{10,100} wrote:",
        r"From: .+\nSent: .+\nTo: ",
        r"From: .+\nDate: .+\nTo: ",
    ]
    parts = re.split("|".join(separators), text, flags=re.IGNORECASE | re.MULTILINE)
    return [p for p in parts if len(p.strip()) > 50]


def parse_whatsapp_export(file_path: Path) -> list:
    text = file_path.read_text(encoding="utf-8", errors="replace")
    line_pattern = re.compile(
        r"(\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}(?:\s*[AP]M)?)\s*-\s*([^:]+):\s*(.*)"
    )
    system_patterns = [
        "end-to-end encrypted", "added", "removed", "left",
        "changed the subject", "changed the group icon", "created group",
    ]

    messages, current = [], None
    for line in text.split("\n"):
        m = line_pattern.match(line)
        if m:
            if current:
                messages.append(current)
            current = {"date": m.group(1).strip(), "sender": m.group(2).strip(), "content": m.group(3).strip()}
        elif current and line.strip():
            current["content"] += " " + line.strip()
    if current:
        messages.append(current)

    messages = [m for m in messages if not any(p.lower() in m["content"].lower() for p in system_patterns)]

    day_groups = {}
    for msg in messages:
        key = msg["date"].split(",")[0].strip()
        day_groups.setdefault(key, []).append(msg)

    chunks = []
    for i, (date_key, day_msgs) in enumerate(sorted(day_groups.items())):
        content = "\n".join(f"{m['sender']}: {m['content']}" for m in day_msgs)
        chunks.append(Chunk(
            chunk_id=_make_id(str(file_path), i),
            source_file=str(file_path),
            source_type="whatsapp",
            date=date_key,
            participants=list(set(m["sender"] for m in day_msgs)),
            content=content[:4000],
        ))
    return chunks


def parse_notes(file_path: Path) -> list:
    text = file_path.read_text(encoding="utf-8", errors="replace")
    parts = re.split(r"\n(?=#{1,3}\s)|(?:\n---+\n)", text)
    chunks = []
    for i, part in enumerate(parts):
        if len(part.strip()) < 30:
            continue
        chunks.append(Chunk(
            chunk_id=_make_id(str(file_path), i),
            source_file=str(file_path),
            source_type="notes",
            date=_extract_date(part),
            participants=[],
            content=part.strip()[:4000],
        ))
    if not chunks:
        chunks.append(Chunk(
            chunk_id=_make_id(str(file_path), 0),
            source_file=str(file_path),
            source_type="notes",
            date="",
            participants=[],
            content=text.strip()[:4000],
        ))
    return chunks


def parse_fetched_url(file_path: Path) -> list:
    text = file_path.read_text(encoding="utf-8", errors="replace")
    url, fetch_date = "", ""
    for line in text.split("\n")[:5]:
        if line.startswith("# Source:"):
            url = line.replace("# Source:", "").strip()
        elif line.startswith("# Fetched:"):
            fetch_date = line.replace("# Fetched:", "").strip()
    return [Chunk(
        chunk_id=_make_id(str(file_path), 0),
        source_file=str(file_path),
        source_type="fetched_url",
        date=fetch_date,
        participants=[],
        content=text.strip()[:6000],
    )]
