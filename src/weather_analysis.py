"""Weather-feed normalization and simple session-weather summaries."""

from __future__ import annotations

import pandas as pd


WEATHER_COLUMNS = ("AirTemp", "TrackTemp", "Humidity", "Pressure", "WindSpeed", "WindDirection")


def _relative_seconds(values: pd.Series) -> pd.Series:
    """Convert timedelta or timestamp values to seconds from the first sample."""
    if pd.api.types.is_timedelta64_dtype(values):
        return values.dt.total_seconds()
    timestamps = pd.to_datetime(values, errors="coerce")
    return (timestamps - timestamps.min()).dt.total_seconds()


def clean_weather(weather: pd.DataFrame) -> pd.DataFrame:
    """Return weather observations with numeric channels and relative time."""
    if weather is None or weather.empty:
        return pd.DataFrame()
    data = weather.copy()
    if "Time" in data:
        data["Elapsed time (s)"] = _relative_seconds(data["Time"])
    for column in WEATHER_COLUMNS:
        if column in data:
            data[column] = pd.to_numeric(data[column], errors="coerce")
    return data


def weather_summary(weather: pd.DataFrame) -> dict[str, str | int]:
    """Return observed ranges without filling missing values."""
    data = clean_weather(weather)
    if data.empty:
        return {"Records": 0, "Air temperature": "—", "Track temperature": "—", "Humidity": "—", "Wind speed": "—", "Pressure": "—", "Rain samples": "—"}
    def range_text(column: str, unit: str) -> str:
        if column not in data or data[column].dropna().empty:
            return "—"
        values = data[column].dropna()
        return f"{values.min():.1f}–{values.max():.1f} {unit}"
    rain = int(data["Rainfall"].fillna(False).astype(bool).sum()) if "Rainfall" in data else 0
    return {
        "Records": len(data),
        "Air temperature": range_text("AirTemp", "°C"),
        "Track temperature": range_text("TrackTemp", "°C"),
        "Humidity": range_text("Humidity", "%"),
        "Wind speed": range_text("WindSpeed", "m/s"),
        "Pressure": range_text("Pressure", "hPa"),
        "Rain samples": rain,
    }
