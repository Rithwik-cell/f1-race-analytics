"""Reusable, defensive transformations for FastF1 timing data."""

from __future__ import annotations

from typing import Any

import pandas as pd


def clean_laps(laps: pd.DataFrame) -> pd.DataFrame:
    """Return a normalized copy while preserving FastF1 quality indicators."""
    if laps is None:
        return pd.DataFrame()
    cleaned = laps.copy()
    for column in ("LapTime", "Sector1Time", "Sector2Time", "Sector3Time"):
        if column in cleaned:
            cleaned[column] = pd.to_timedelta(cleaned[column], errors="coerce")
    for column in ("LapNumber", "Position", "Stint", "TyreLife"):
        if column in cleaned:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    return cleaned


def get_valid_laps(laps: pd.DataFrame) -> pd.DataFrame:
    """Filter to usable lap times without hiding the original records."""
    cleaned = clean_laps(laps)
    if cleaned.empty or "LapTime" not in cleaned:
        return cleaned.iloc[0:0].copy()
    valid = cleaned[cleaned["LapTime"].notna()].copy()
    if "IsAccurate" in valid:
        valid = valid[valid["IsAccurate"].fillna(True)]
    if "Deleted" in valid:
        valid = valid[~valid["Deleted"].fillna(False)]
    return valid


def get_driver_laps(laps: pd.DataFrame, driver: str) -> pd.DataFrame:
    """Return all records for a driver, including invalid records for QA."""
    cleaned = clean_laps(laps)
    if cleaned.empty or "Driver" not in cleaned:
        return cleaned.iloc[0:0].copy()
    return cleaned[cleaned["Driver"].eq(driver)].copy()


def get_fastest_lap(laps: pd.DataFrame) -> pd.Series | None:
    """Return the fastest valid lap record, or ``None`` when unavailable."""
    valid = get_valid_laps(laps)
    if valid.empty:
        return None
    return valid.loc[valid["LapTime"].idxmin()]


def calculate_average_lap(laps: pd.DataFrame) -> pd.Timedelta | None:
    """Calculate an average from valid laps only."""
    valid = get_valid_laps(laps)
    if valid.empty:
        return None
    return valid["LapTime"].mean()


def calculate_sector_statistics(laps: pd.DataFrame) -> pd.DataFrame:
    """Return best sector times by driver from valid, non-deleted laps."""
    valid = get_valid_laps(laps)
    if valid.empty or "Driver" not in valid:
        return pd.DataFrame()
    sectors = [c for c in ("Sector1Time", "Sector2Time", "Sector3Time") if c in valid]
    if not sectors:
        return pd.DataFrame()
    return valid.groupby("Driver", as_index=False)[sectors].min()


def format_timedelta(value: Any) -> str:
    """Format a duration as a readable lap time without exposing NaT."""
    if pd.isna(value):
        return "—"
    duration = pd.to_timedelta(value, errors="coerce")
    if pd.isna(duration):
        return "—"
    seconds = duration.total_seconds()
    if seconds >= 60:
        minutes = int(seconds // 60)
        remainder = seconds - minutes * 60
        return f"{minutes}:{remainder:06.3f}"
    return f"{seconds:.3f} s"
