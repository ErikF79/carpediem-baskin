"""Utility per le stagioni sportive (1 luglio - 30 giugno)."""
from __future__ import annotations

import re
from datetime import date

SEASON_RE = re.compile(r"^\s*(\d{4})\s*[/\-]\s*(\d{4})\s*$")


def season_range(label: str | None) -> tuple[date, date] | None:
    if not label:
        return None
    match = SEASON_RE.match(label)
    if not match:
        return None
    start_year, end_year = int(match.group(1)), int(match.group(2))
    return date(start_year, 7, 1), date(end_year, 6, 30)


def current_season_label(today: date | None = None) -> str:
    today = today or date.today()
    year = today.year if today.month >= 7 else today.year - 1
    return f"{year}/{year + 1}"
