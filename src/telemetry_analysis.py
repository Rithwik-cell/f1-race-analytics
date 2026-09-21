"""FastF1 telemetry extraction and distance-aligned comparison helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd


class TelemetryUnavailableError(RuntimeError):
    """Raised when a selected lap has no usable telemetry."""


TELEMETRY_CHANNELS = ("Speed", "Throttle", "Brake", "RPM", "nGear", "Distance")


def telemetry_lap_options(laps: pd.DataFrame, driver: str) -> list[int]:
    """Return available lap numbers for a driver, prioritizing usable lap records."""
    if laps is None or laps.empty or not {"Driver", "LapNumber"}.issubset(laps.columns):
        return []
    selected = laps[laps["Driver"].eq(driver)].copy()
    if "LapTime" in selected:
        selected = selected[selected["LapTime"].notna()]
    numbers = pd.to_numeric(selected["LapNumber"], errors="coerce").dropna().astype(int).unique()
    return sorted(numbers.tolist())


def get_lap_telemetry(session, driver: str, lap_number: int) -> pd.DataFrame:
    """Load telemetry for one FastF1 lap and return a normalized DataFrame."""
    try:
        laps = session.laps.pick_drivers(driver).pick_laps(lap_number)
        if laps.empty:
            raise TelemetryUnavailableError(f"No lap {lap_number} is available for {driver}.")
        lap = laps.pick_fastest()
        telemetry = lap.get_telemetry()
    except TelemetryUnavailableError:
        raise
    except Exception as exc:
        raise TelemetryUnavailableError(f"Telemetry is unavailable for {driver} lap {lap_number}.") from exc
    if telemetry is None or telemetry.empty:
        raise TelemetryUnavailableError(f"Telemetry is unavailable for {driver} lap {lap_number}.")
    return prepare_telemetry(telemetry)


def prepare_telemetry(telemetry: pd.DataFrame) -> pd.DataFrame:
    """Keep common channels, coerce numeric values, and remove unusable distances."""
    data = telemetry.copy()
    for column in TELEMETRY_CHANNELS:
        if column in data:
            data[column] = pd.to_numeric(data[column], errors="coerce")
    if "Distance" not in data:
        raise TelemetryUnavailableError("Telemetry has no distance channel for alignment.")
    data = data.dropna(subset=["Distance"]).sort_values("Distance")
    data["Distance"] = data["Distance"] - data["Distance"].min()
    return data.loc[:, [column for column in data.columns if column in set(TELEMETRY_CHANNELS) or column in ("Time", "SessionTime", "DriverAhead", "DRS")]].reset_index(drop=True)


def resample_by_distance(telemetry: pd.DataFrame, samples: int = 300) -> pd.DataFrame:
    """Interpolate numeric telemetry channels onto a common distance grid."""
    if telemetry is None or telemetry.empty or "Distance" not in telemetry:
        return pd.DataFrame()
    data = prepare_telemetry(telemetry)
    if len(data) < 2 or data["Distance"].nunique() < 2:
        return data
    grid = np.linspace(float(data["Distance"].min()), float(data["Distance"].max()), samples)
    aligned = pd.DataFrame({"Distance": grid})
    for column in ("Speed", "Throttle", "Brake", "RPM", "nGear"):
        if column in data:
            valid = data[["Distance", column]].dropna()
            if len(valid) >= 2:
                aligned[column] = np.interp(grid, valid["Distance"], valid[column])
    return aligned


def telemetry_summary(telemetry: pd.DataFrame) -> dict[str, str | int]:
    """Return compact metadata for a telemetry panel."""
    if telemetry is None or telemetry.empty:
        return {"Samples": 0, "Distance": "—"}
    distance = telemetry["Distance"].max() - telemetry["Distance"].min() if "Distance" in telemetry else np.nan
    return {
        "Samples": len(telemetry),
        "Distance": f"{distance:.0f} m" if pd.notna(distance) else "—",
        "Channels": int(sum(channel in telemetry for channel in TELEMETRY_CHANNELS)),
    }
