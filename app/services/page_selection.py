"""Parse and validate page selection for PDF conversion."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageSelection:
    pages: list[int]  # 1-based, sorted, unique


def parse_pages(spec: str) -> PageSelection:
    """Parse a pages spec like '1-3,5,7-10' into a sorted unique list."""
    raw = (spec or "").strip()
    if not raw:
        return PageSelection(pages=[])

    pages: set[int] = set()
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    for part in parts:
        if "-" in part:
            a, b = [x.strip() for x in part.split("-", 1)]
            if not a.isdigit() or not b.isdigit():
                raise ValueError("Invalid range")
            start = int(a)
            end = int(b)
            if start <= 0 or end <= 0:
                raise ValueError("Pages must be positive")
            if end < start:
                start, end = end, start
            for i in range(start, end + 1):
                pages.add(i)
        else:
            if not part.isdigit():
                raise ValueError("Invalid page")
            p = int(part)
            if p <= 0:
                raise ValueError("Pages must be positive")
            pages.add(p)

    return PageSelection(pages=sorted(pages))


def validate_pages(pages: list[int], *, total_pages: int, max_selected: int | None = None) -> None:
    if not pages:
        raise ValueError("No pages selected")
    if any(p < 1 or p > total_pages for p in pages):
        raise ValueError("Selected pages out of range")
    if max_selected is not None and len(pages) > max_selected:
        raise ValueError("Too many pages selected")
