"""Race-control, track-status, and unified timeline preparation."""

from __future__ import annotations

import pandas as pd


def _relative_seconds(values: pd.Series) -> pd.Series:
    if pd.api.types.is_timedelta64_dtype(values):
        return values.dt.total_seconds()
    timestamps = pd.to_datetime(values, errors="coerce")
    return (timestamps - timestamps.min()).dt.total_seconds()


def clean_race_control_messages(messages: pd.DataFrame) -> pd.DataFrame:
    """Normalize race-control records while retaining the original message."""
    if messages is None or messages.empty:
        return pd.DataFrame()
    data = messages.copy()
    if "Time" in data:
        data["Elapsed time (s)"] = _relative_seconds(data["Time"])
    if "Lap" in data:
        data["Lap"] = pd.to_numeric(data["Lap"], errors="coerce")
    for column in ("Category", "Message", "Status", "Flag", "Scope", "Sector", "RacingNumber"):
        if column in data:
            data[column] = data[column].fillna("Unavailable").astype(str)
    return data


def clean_track_status(status: pd.DataFrame) -> pd.DataFrame:
    """Normalize track-status intervals and retain FastF1 status labels."""
    if status is None or status.empty:
        return pd.DataFrame()
    data = status.copy()
    if "Time" in data:
        data["Elapsed time (s)"] = _relative_seconds(data["Time"])
    if "Status" in data:
        data["Status"] = data["Status"].fillna("Unavailable").astype(str)
    if "Message" in data:
        data["Message"] = data["Message"].fillna("Unavailable").astype(str)
    return data


def build_race_timeline(laps: pd.DataFrame, stints: pd.DataFrame, pit_stops: pd.DataFrame, track_status: pd.DataFrame, race_control: pd.DataFrame) -> pd.DataFrame:
    """Create an event-oriented timeline from observed race/session records."""
    events: list[dict[str, object]] = []
    if laps is not None and not laps.empty and "LapNumber" in laps:
        for lap in sorted(pd.to_numeric(laps["LapNumber"], errors="coerce").dropna().unique()):
            subset = laps[laps["LapNumber"].eq(lap)]
            positions = []
            if {"Driver", "Position"}.issubset(subset.columns):
                for _, row in subset.dropna(subset=["Driver", "Position"]).iterrows():
                    positions.append(f"{row['Driver']} P{int(row['Position'])}")
            events.append({"Order": float(lap), "Lap": int(lap), "Event type": "Lap", "Driver": "Multiple", "Details": "; ".join(positions[:12]) or "Position data unavailable", "Status": "—"})
    if pit_stops is not None and not pit_stops.empty:
        for _, row in pit_stops.iterrows():
            events.append({"Order": float(row.get("Pit stop lap", 0)), "Lap": row.get("Pit stop lap", pd.NA), "Event type": "Pit stop", "Driver": row.get("Driver", "Unavailable"), "Details": f"{row.get('Previous compound', 'Unavailable')} → {row.get('New compound', 'Unavailable')}", "Status": row.get("Evidence", "Unavailable")})
    if stints is not None and not stints.empty:
        for _, row in stints[stints["Stint"].gt(1)].iterrows():
            events.append({"Order": float(row.get("Start lap", 0)), "Lap": row.get("Start lap", pd.NA), "Event type": "Tyre change", "Driver": row.get("Driver", "Unavailable"), "Details": f"New {row.get('Compound', 'Unavailable')}", "Status": "Stint boundary"})
    for data, event_type in ((clean_track_status(track_status), "Track status"), (clean_race_control_messages(race_control), "Race control")):
        if data.empty:
            continue
        for _, row in data.iterrows():
            lap = row.get("Lap", pd.NA)
            order = float(lap) if pd.notna(lap) else float(row.get("Elapsed time (s)", 0)) / 60.0
            details = row.get("Message", row.get("Status", "Unavailable"))
            events.append({"Order": order, "Lap": lap, "Event type": event_type, "Driver": "—", "Details": details, "Status": row.get("Status", row.get("Flag", "Unavailable"))})
    if not events:
        return pd.DataFrame(columns=["Order", "Lap", "Event type", "Driver", "Details", "Status"])
    return pd.DataFrame(events).sort_values(["Order", "Event type"]).reset_index(drop=True)

