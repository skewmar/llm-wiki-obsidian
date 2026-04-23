from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Chunk:
    chunk_id: str
    source_file: str
    source_type: str  # email | whatsapp | notes | fetched_url
    date: Optional[str]
    participants: list
    content: str


@dataclass
class Entity:
    slug: str
    name: str
    entity_type: str  # person | company | project
    domain: str
    aliases: list
    description: str
    source_files: list
    status: str = "CREATE"  # CREATE | UPDATE


@dataclass
class Concept:
    slug: str
    name: str
    domain: str
    aliases: list
    description: str
    source_files: list
    status: str = "CREATE"  # CREATE | UPDATE


@dataclass
class Relationship:
    from_slug: str
    to_slug: str
    relationship_type: str
    notes: str = ""


@dataclass
class ExtractedKnowledge:
    entities: list = field(default_factory=list)
    concepts: list = field(default_factory=list)
    relationships: list = field(default_factory=list)
