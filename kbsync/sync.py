"""Decide what has to change in the knowledge base. Pure logic, no I/O."""

import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class LocalDoc:
    article_id: str
    title: str
    url: str
    updated_at: str
    path: Path
    content_hash: str


@dataclass(frozen=True)
class RemoteDoc:
    name: str  # fileSearchStores/<store>/documents/<doc>
    article_id: str
    content_hash: str


@dataclass
class SyncPlan:
    to_add: list[LocalDoc] = field(default_factory=list)
    to_update: list[tuple[LocalDoc, list[RemoteDoc]]] = field(default_factory=list)
    unchanged: list[LocalDoc] = field(default_factory=list)
    to_remove: list[RemoteDoc] = field(default_factory=list)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def plan_sync(local: list[LocalDoc], remote: list[RemoteDoc], prune: bool) -> SyncPlan:
    """Compare by content hash, so a change in either the article or our cleaner triggers a re-upload.

    `prune` removes remote documents whose article no longer exists; only safe after a full scrape.
    """
    remote_by_id: dict[str, list[RemoteDoc]] = {}
    for doc in remote:
        remote_by_id.setdefault(doc.article_id, []).append(doc)

    plan = SyncPlan()
    for doc in local:
        existing = remote_by_id.pop(doc.article_id, [])
        if not existing:
            plan.to_add.append(doc)
        elif len(existing) == 1 and existing[0].content_hash == doc.content_hash:
            plan.unchanged.append(doc)
        else:
            # Changed content, or duplicates left behind by an interrupted run: replace them all.
            plan.to_update.append((doc, existing))
    if prune:
        plan.to_remove = [d for docs in remote_by_id.values() for d in docs]
    return plan


def estimate_chunks(text: str, max_tokens: int, overlap: int) -> int:
    """Mirror Gemini's whitespace chunker: windows of `max_tokens` words stepping by `max_tokens - overlap`."""
    words = len(text.split())
    if words <= max_tokens:
        return 1
    return 1 + math.ceil((words - max_tokens) / (max_tokens - overlap))
