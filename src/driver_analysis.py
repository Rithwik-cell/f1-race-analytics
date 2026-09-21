"""Driver-level metrics derived from FastF1 session data."""

from __future__ import annotations

import pandas as pd

from .data_processing import calculate_average_lap, format_timedelta, get_driver_laps, get_fastest_lap, get_valid_laps


def _result_row(results: pd.DataFrame, driver: str) -> pd.Series:
    if results is None or results.empty or "Abbreviation" not in results:
        return pd.Series(dtype="object")
    matches = results[results["Abbreviation"].eq(driver)]
    return matches.iloc[0] if not matches.empty else pd.Series(dtype="object")


def driver_options(laps: pd.DataFrame) -> list[str]:
    """Return available driver abbreviations in stable display order."""
    if laps is None or laps.empty or "Driver" not in laps:
        return []
    return sorted(laps["Driver"].dropna().astype(str).unique())


def build_driver_summary(laps: pd.DataFrame, results: pd.DataFrame, driver: str) -> dict[str, object]:
    """Build a display-ready summary while leaving missing values explicit."""
    driver_laps = get_driver_laps(laps, driver)
    valid = get_valid_laps(driver_laps)
    fastest = get_fastest_lap(driver_laps)
    result = _result_row(results, driver)
    summary: dict[str, object] = {
        "Driver": driver,
        "Team": result.get("TeamName", "—"),
        "Position": result.get("Position", "—"),
        "Grid": result.get("GridPosition", "—"),
        "Points": result.get("Points", "—"),
        "Records": len(driver_laps),
        "Valid laps": len(valid),
        "Average lap": format_timedelta(calculate_average_lap(driver_laps)),
        "Fastest lap": format_timedelta(fastest["LapTime"] if fastest is not None else pd.NaT),
    }
    if "SpeedFL" in valid:
        summary["Best finish-line speed"] = f"{valid['SpeedFL'].max():.1f} km/h" if valid["SpeedFL"].notna().any() else "—"
    if "Compound" in driver_laps:
        compounds = driver_laps["Compound"].dropna().astype(str).unique()
        summary["Compounds"] = ", ".join(compounds) if len(compounds) else "—"
    return summary


def driver_lap_data(laps: pd.DataFrame, driver: str) -> pd.DataFrame:
    """Return driver laps with readable seconds and a validity label."""
    records = get_driver_laps(laps, driver)
    if records.empty:
        return records
    records = records.copy()
    records["Lap time (s)"] = records["LapTime"].dt.total_seconds()
    records["Validity"] = "Valid"
    if "LapTime" in records:
        records.loc[records["LapTime"].isna(), "Validity"] = "Missing time"
    if "IsAccurate" in records:
        records.loc[records["IsAccurate"].eq(False), "Validity"] = "Inaccurate"
    if "Deleted" in records:
        records.loc[records["Deleted"].eq(True), "Validity"] = "Deleted"
    return records

