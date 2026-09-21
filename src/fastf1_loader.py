"""FastF1 session loading with a project-local cache and friendly errors."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import fastf1
import pandas as pd

from .config import CACHE_DIR, ensure_project_directories

LOGGER = logging.getLogger(__name__)
_CACHE_ENABLED = False


class SessionLoadError(RuntimeError):
    """Raised when FastF1 cannot load the requested session."""


@dataclass(frozen=True)
class SessionRequest:
    season: int
    event: str
    session_type: str


def configure_fastf1_cache() -> None:
    """Enable FastF1's persistent cache once per process."""
    global _CACHE_ENABLED
    if not _CACHE_ENABLED:
        ensure_project_directories()
        fastf1.Cache.enable_cache(str(CACHE_DIR))
        _CACHE_ENABLED = True
        LOGGER.info("FastF1 cache enabled at %s", CACHE_DIR)


def load_session(season: int, event: str, session_type: str) -> Any:
    """Load and return a FastF1 session.

    FastF1 performs the actual download and parsing. Warnings are left visible
    to logs because incomplete timing data is common, but load failures become a
    concise application-level exception for the dashboard.
    """
    configure_fastf1_cache()
    request = SessionRequest(int(season), str(event), str(session_type))
    try:
        session = fastf1.get_session(
            request.season, request.event, request.session_type
        )
        session.load()
        return session
    except Exception as exc:  # FastF1 raises several backend-specific errors.
        LOGGER.exception("Unable to load FastF1 session %s", request)
        raise SessionLoadError(
            f"Could not load {request.season} {request.event} "
            f"({request.session_type}). Check the event/session and network connection."
        ) from exc


def get_event_options(season: int) -> list[str]:
    """Return FastF1 event names for a season, with a safe fallback."""
    configure_fastf1_cache()
    try:
        schedule = fastf1.get_event_schedule(int(season), include_testing=False)
        if "EventName" in schedule:
            values = schedule["EventName"].dropna().astype(str).tolist()
            return list(dict.fromkeys(values))
    except Exception:
        LOGGER.exception("Unable to retrieve event schedule for %s", season)
    return []


def get_session_options(season: int, event: str) -> list[str]:
    """Return supported FastF1 session codes for one scheduled event."""
    configure_fastf1_cache()
    session_map = {
        "Practice 1": "FP1",
        "Practice 2": "FP2",
        "Practice 3": "FP3",
        "Qualifying": "Q",
        "Sprint Qualifying": "SQ",
        "Sprint Shootout": "SQ",
        "Sprint": "Sprint",
        "Race": "R",
    }
    try:
        schedule = fastf1.get_event_schedule(int(season), include_testing=False)
        matches = schedule[
            schedule["EventName"].astype(str).str.casefold().eq(str(event).casefold())
            | schedule["Location"].astype(str).str.casefold().eq(str(event).casefold())
        ]
        if matches.empty:
            return []
        row = matches.iloc[0]
        options = []
        for number in range(1, 6):
            value = row.get(f"Session{number}")
            if pd.notna(value) and str(value) in session_map:
                options.append(session_map[str(value)])
        return list(dict.fromkeys(options))
    except Exception:
        LOGGER.exception("Unable to retrieve sessions for %s %s", season, event)
        return []
