"""Tyre stints, degradation trends, and pit-stop evidence from FastF1 laps."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .data_processing import get_valid_laps


def stint_table(laps: pd.DataFrame) -> pd.DataFrame:
    """Summarize observed tyre stints by driver and stint number.

    A stint is grouped from FastF1's reported ``Stint`` and ``Compound`` fields.
    The table does not infer missing laps between records.
    """
    if laps is None or laps.empty or not {"Driver", "Stint", "Compound", "LapNumber"}.issubset(laps.columns):
        return pd.DataFrame()
    cleaned = laps.copy()
    cleaned["LapNumber"] = pd.to_numeric(cleaned["LapNumber"], errors="coerce")
    cleaned["Stint"] = pd.to_numeric(cleaned["Stint"], errors="coerce")
    cleaned = cleaned.dropna(subset=["Driver", "Stint", "Compound", "LapNumber"])
    if cleaned.empty:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    for (driver, stint, compound), group in cleaned.groupby(["Driver", "Stint", "Compound"], sort=True):
        valid = get_valid_laps(group)
        average = valid["LapTime"].dt.total_seconds().mean() if not valid.empty else np.nan
        best = valid["LapTime"].dt.total_seconds().min() if not valid.empty else np.nan
        fresh = group["FreshTyre"].dropna().iloc[0] if "FreshTyre" in group and group["FreshTyre"].notna().any() else pd.NA
        rows.append({
            "Driver": driver,
            "Stint": int(stint),
            "Compound": str(compound),
            "Start lap": int(group["LapNumber"].min()),
            "End lap": int(group["LapNumber"].max()),
            "Stint length": int(group["LapNumber"].nunique()),
            "Fresh tyre": fresh,
            "Average lap (s)": average,
            "Best lap (s)": best,
        })
    return pd.DataFrame(rows).sort_values(["Driver", "Start lap"]).reset_index(drop=True)


def tyre_life_data(laps: pd.DataFrame, driver: str, compound: str) -> pd.DataFrame:
    """Return valid lap time versus tyre life for one driver/compound."""
    if laps is None or laps.empty or not {"Driver", "Compound", "TyreLife", "LapTime"}.issubset(laps.columns):
        return pd.DataFrame()
    selected = laps[laps["Driver"].eq(driver) & laps["Compound"].eq(compound)].copy()
    valid = get_valid_laps(selected).copy()
    if valid.empty:
        return pd.DataFrame()
    valid["Tyre life"] = pd.to_numeric(valid["TyreLife"], errors="coerce")
    valid["Lap time (s)"] = valid["LapTime"].dt.total_seconds()
    return valid.dropna(subset=["Tyre life", "Lap time (s)"]).sort_values("Tyre life")


def degradation_estimate(data: pd.DataFrame) -> dict[str, float | int | str]:
    """Estimate a simple observed lap-time trend against tyre life.

    The result is deliberately labeled as an association. Traffic, safety cars,
    track evolution, fuel load, and driver management are not controlled here.
    """
    if data is None or len(data) < 3 or not {"Tyre life", "Lap time (s)"}.issubset(data.columns):
        return {"status": "insufficient data", "points": int(len(data)) if data is not None else 0}
    x = data["Tyre life"].to_numpy(dtype=float)
    y = data["Lap time (s)"].to_numpy(dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 3 or np.ptp(x[mask]) == 0:
        return {"status": "insufficient tyre-life variation", "points": int(mask.sum())}
    slope, intercept = np.polyfit(x[mask], y[mask], 1)
    predicted = slope * x[mask] + intercept
    ss_res = float(np.sum((y[mask] - predicted) ** 2))
    ss_tot = float(np.sum((y[mask] - y[mask].mean()) ** 2))
    r_squared = 1 - ss_res / ss_tot if ss_tot else 0.0
    return {
        "status": "estimated",
        "points": int(mask.sum()),
        "slope_seconds_per_lap": float(slope),
        "intercept_seconds": float(intercept),
        "r_squared": float(r_squared),
    }


def pit_stop_table(laps: pd.DataFrame) -> pd.DataFrame:
    """Identify pit-stop evidence from PitInTime/PitOutTime markers.

    Exact pit-lane duration is intentionally not calculated because timing-feed
    markers do not always provide a reliable entry-to-exit interval.
    """
    required = {"Driver", "LapNumber", "Compound"}
    if laps is None or laps.empty or not required.issubset(laps.columns):
        return pd.DataFrame()
    records: list[dict[str, object]] = []
    for driver, group in laps.groupby("Driver", sort=True):
        group = group.sort_values("LapNumber").reset_index(drop=True)
        pit_in_mask = group["PitInTime"].notna() if "PitInTime" in group else pd.Series(False, index=group.index)
        pit_out_mask = group["PitOutTime"].notna() if "PitOutTime" in group else pd.Series(False, index=group.index)
        for index in group.index[pit_in_mask]:
            current = group.loc[index]
            following = group.loc[index + 1 :]
            out_rows = following[pit_out_mask.loc[following.index]] if not following.empty else following
            new_compound = out_rows.iloc[0]["Compound"] if not out_rows.empty else (following.iloc[0]["Compound"] if not following.empty else None)
            new_compound = str(new_compound) if pd.notna(new_compound) else "Unavailable"
            stint_value = current.get("Stint", None)
            records.append({
                "Driver": driver,
                "Pit stop lap": current["LapNumber"],
                "Previous compound": str(current["Compound"]) if pd.notna(current["Compound"]) else "Unavailable",
                "New compound": new_compound,
                "Stint number": str(stint_value) if pd.notna(stint_value) else "Unavailable",
                "Evidence": "PitInTime + following lap",
            })
        if not pit_in_mask.any():
            for index in group.index[pit_out_mask]:
                current = group.loc[index]
                previous = group.loc[index - 1] if index > 0 else None
                previous_compound = previous["Compound"] if previous is not None else None
                stint_value = current.get("Stint", None)
                records.append({
                    "Driver": driver,
                    "Pit stop lap": current["LapNumber"],
                    "Previous compound": str(previous_compound) if pd.notna(previous_compound) else "Unavailable",
                    "New compound": str(current["Compound"]) if pd.notna(current["Compound"]) else "Unavailable",
                    "Stint number": str(stint_value) if pd.notna(stint_value) else "Unavailable",
                    "Evidence": "PitOutTime marker",
                })
    return pd.DataFrame(records).sort_values(["Pit stop lap", "Driver"]).reset_index(drop=True) if records else pd.DataFrame()
