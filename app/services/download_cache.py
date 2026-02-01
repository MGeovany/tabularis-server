"""In-memory cache for conversion outputs (XLSX bytes).

Tabularis-server does not store PDFs or XLSX on disk. This cache enables a short-lived
"download again" experience from the UI after a conversion is completed.

Notes:
- Best effort: data is lost on process restart.
- TTL-based eviction to keep memory bounded.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CacheItem:
    created_at: float
    data: bytes


_store: dict[UUID, CacheItem] = {}

# Conservative defaults; can be made configurable later.
_TTL_SEC = 10 * 60
_MAX_ITEMS = 200


def _cleanup(now: float) -> None:
    # TTL eviction
    expired = [k for k, v in _store.items() if (now - v.created_at) > _TTL_SEC]
    for k in expired:
        _store.pop(k, None)

    # Size-based eviction (oldest first)
    if len(_store) <= _MAX_ITEMS:
        return
    items = sorted(_store.items(), key=lambda kv: kv[1].created_at)
    for k, _ in items[: max(0, len(_store) - _MAX_ITEMS)]:
        _store.pop(k, None)


def put(conversion_id: UUID, data: bytes) -> None:
    now = time.monotonic()
    _cleanup(now)
    _store[conversion_id] = CacheItem(created_at=now, data=data)


def get(conversion_id: UUID) -> bytes | None:
    now = time.monotonic()
    _cleanup(now)
    item = _store.get(conversion_id)
    return item.data if item else None
