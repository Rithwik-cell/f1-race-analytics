"""Team and driver-comparison metrics built from FastF1 results and laps."""

from __future__ import annotations

import pandas as pd

from .data_processing import calculate_average_lap, get_driver_laps, get_fastest_lap, get_valid_laps
from .lap_analysis import sector_table


def team_options(results: pd.DataFrame, laps: pd.DataFrame | None = None) -> list[str]:
    """Return teams observed in results or lap records."""
    values: set[str] = set()
    if results is not None and "TeamName" in results:
        values.update(results["TeamName"].dropna().astype(str))
    if laps is not None and "Team" in laps:
        values.update(laps["Team"].dropna().astype(str))
    return sorted(values)


def team_summary(laps: pd.DataFrame, results: pd.DataFrame, team: str) -> dict[str, object]:
    """Summarize the selected team without assuming two complete drivers."""
    result_rows = results[results["TeamName"].eq(team)].copy() if results is not None and not results.empty and "TeamName" in results else pd.DataFrame()
    team_laps = laps[laps["Team"].eq(team)].copy() if laps is not None and not laps.empty and "Team" in laps else pd.DataFrame()
    valid = get_valid_laps(team_laps)
    fastest = get_fastest_lap(team_laps)
    drivers = result_rows["Abbreviation"].dropna().astype(str).tolist() if "Abbreviation" in result_rows else sorted(team_laps["Driver"].dropna().astype(str).unique().tolist())
    return {
        "Team": team,
        "Drivers": ", ".join(drivers) if drivers else "Unavailable",
        "Average lap": f"{calculate_average_lap(team_laps).total_seconds():.3f} s" if calculate_average_lap(team_laps) is not None else "—",
        "Fastest lap": f"{fastest['LapTime'].total_seconds():.3f} s" if fastest is not None else "—",
        "Valid laps": len(valid),
        "Points": float(result_rows["Points"].sum()) if "Points" in result_rows else 0.0,
        "Top speed": f"{valid['SpeedFL'].max():.1f} km/h" if "SpeedFL" in valid and valid["SpeedFL"].notna().any() else "—",
    }


def team_performance_table(laps: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
    """Return one comparable row per team."""
    rows = [team_summary(laps, results, team) for team in team_options(results, laps)]
    return pd.DataFrame(rows).sort_values(["Points", "Fastest lap"], ascending=[False, True]).reset_index(drop=True) if rows else pd.DataFrame()


def driver_comparison_table(laps: pd.DataFrame, results: pd.DataFrame, driver_a: str, driver_b: str) -> pd.DataFrame:
    """Compare two drivers using valid lap and sector observations."""
    sectors = sector_table(laps).set_index("Driver") if not sector_table(laps).empty else pd.DataFrame()
    rows = []
    for label, driver in (("Driver A", driver_a), ("Driver B", driver_b)):
        driver_laps = get_driver_laps(laps, driver)
        valid = get_valid_laps(driver_laps)
        fastest = get_fastest_lap(driver_laps)
        row = {"Selection": label, "Driver": driver, "Fastest lap (s)": fastest["LapTime"].total_seconds() if fastest is not None else None, "Average lap (s)": calculate_average_lap(driver_laps).total_seconds() if calculate_average_lap(driver_laps) is not None else None, "Valid laps": len(valid), "Top speed (km/h)": valid["SpeedFL"].max() if "SpeedFL" in valid and valid["SpeedFL"].notna().any() else None}
        if driver in sectors.index:
            for column in ("Best S1 (s)", "Best S2 (s)", "Best S3 (s)", "Theoretical best (s)"):
                if column in sectors:
                    row[column] = sectors.loc[driver, column]
        rows.append(row)
    return pd.DataFrame(rows)


def comparison_lap_data(laps: pd.DataFrame, driver_a: str, driver_b: str) -> pd.DataFrame:
    """Return same-lap-number lap times and A-minus-B delta."""
    frames = []
    for driver, label in ((driver_a, "Driver A"), (driver_b, "Driver B")):
        valid = get_valid_laps(get_driver_laps(laps, driver))
        if valid.empty:
            continue
        data = valid[["LapNumber", "LapTime"]].copy()
        data["Driver"] = label
        data["Lap time (s)"] = data["LapTime"].dt.total_seconds()
        frames.append(data[["LapNumber", "Driver", "Lap time (s)"]])
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    pivot = combined.pivot_table(index="LapNumber", columns="Driver", values="Lap time (s)", aggfunc="mean").reset_index()
    if {"Driver A", "Driver B"}.issubset(pivot.columns):
        pivot["Delta A - B (s)"] = pivot["Driver A"] - pivot["Driver B"]
    return pivot

