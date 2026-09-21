"""Lap-level analysis helpers for charts and quality reporting."""

from __future__ import annotations

import pandas as pd

from .data_processing import clean_laps, get_valid_laps


def lap_statistics(laps: pd.DataFrame) -> dict[str, str]:
    """Return descriptive statistics from valid lap times only."""
    valid = get_valid_laps(laps)
    if valid.empty:
        return {key: "—" for key in ("Minimum", "Maximum", "Mean", "Median", "Std. deviation")}
    seconds = valid["LapTime"].dt.total_seconds()
    return {
        "Minimum": f"{seconds.min():.3f} s",
        "Maximum": f"{seconds.max():.3f} s",
        "Mean": f"{seconds.mean():.3f} s",
        "Median": f"{seconds.median():.3f} s",
        "Std. deviation": f"{seconds.std():.3f} s" if len(seconds) > 1 else "—",
    }


def sector_table(laps: pd.DataFrame) -> pd.DataFrame:
    """Return best sector 1/2/3 values and theoretical best lap by driver."""
    valid = get_valid_laps(laps)
    if valid.empty or "Driver" not in valid:
        return pd.DataFrame()
    sector_columns = [c for c in ("Sector1Time", "Sector2Time", "Sector3Time") if c in valid]
    if not sector_columns:
        return pd.DataFrame()
    result = valid.groupby("Driver", as_index=False)[sector_columns].min()
    for column in sector_columns:
        result[column] = result[column].dt.total_seconds()
    renamed = result.rename(columns={
        "Sector1Time": "Best S1 (s)",
        "Sector2Time": "Best S2 (s)",
        "Sector3Time": "Best S3 (s)",
    })
    best_columns = [c for c in ("Best S1 (s)", "Best S2 (s)", "Best S3 (s)") if c in renamed]
    renamed["Theoretical best (s)"] = renamed[best_columns].sum(axis=1, min_count=len(best_columns))
    return renamed


def quality_summary(laps: pd.DataFrame) -> dict[str, int]:
    """Count raw, valid, deleted, inaccurate, and missing-time records."""
    cleaned = clean_laps(laps)
    if cleaned.empty:
        return {key: 0 for key in ("Raw records", "Valid records", "Missing lap times", "Deleted laps", "Inaccurate laps")}
    return {
        "Raw records": len(cleaned),
        "Valid records": len(get_valid_laps(cleaned)),
        "Missing lap times": int(cleaned["LapTime"].isna().sum()) if "LapTime" in cleaned else 0,
        "Deleted laps": int(cleaned["Deleted"].fillna(False).sum()) if "Deleted" in cleaned else 0,
        "Inaccurate laps": int((~cleaned["IsAccurate"].fillna(True)).sum()) if "IsAccurate" in cleaned else 0,
    }

