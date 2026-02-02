"""Helpers for monthly usage windows (FREE: 10 conversions per month)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class UsageWindow:
    period_start: datetime
    reset_at: datetime


def current_month_window(now: datetime | None = None) -> UsageWindow:
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        reset = start.replace(year=start.year + 1, month=1)
    else:
        reset = start.replace(month=start.month + 1)
    return UsageWindow(period_start=start, reset_at=reset)
