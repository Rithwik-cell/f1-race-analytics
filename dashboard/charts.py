"""Plotly chart builders kept separate from Streamlit layout code."""

from __future__ import annotations

import plotly.express as px
import pandas as pd


def position_chart(laps: pd.DataFrame):
    """Build a position progression chart from available lap records."""
    columns = [c for c in ("LapNumber", "Position", "Driver", "Compound") if c in laps]
    chart_data = laps[columns].dropna(subset=["LapNumber", "Position", "Driver"])
    figure = px.line(
        chart_data,
        x="LapNumber",
        y="Position",
        color="Driver",
        hover_data=[c for c in ("Compound",) if c in chart_data],
        markers=False,
        labels={"LapNumber": "Lap", "Position": "Race position"},
        template="plotly_dark",
    )
    figure.update_yaxes(autorange="reversed", dtick=1)
    figure.update_layout(legend_title_text="Driver", height=520)
    return figure


def lap_time_chart(laps: pd.DataFrame, driver: str | None = None):
    """Build a lap-time chart in seconds, preserving invalid points for context."""
    data = laps.copy()
    if driver is not None and "Driver" in data:
        data = data[data["Driver"].eq(driver)]
    if data.empty or "LapNumber" not in data or "LapTime" not in data:
        return px.line(template="plotly_dark")
    data["Lap time (s)"] = data["LapTime"].dt.total_seconds()
    data["Validity"] = "Valid"
    if "LapTime" in data:
        data.loc[data["LapTime"].isna(), "Validity"] = "Missing time"
    if "IsAccurate" in data:
        data.loc[data["IsAccurate"].eq(False), "Validity"] = "Inaccurate"
    if "Deleted" in data:
        data.loc[data["Deleted"].eq(True), "Validity"] = "Deleted"
    figure = px.scatter(
        data,
        x="LapNumber",
        y="Lap time (s)",
        color="Validity",
        hover_data=[c for c in ("Driver", "Compound", "TyreLife", "Position", "TrackStatus") if c in data],
        template="plotly_dark",
        labels={"LapNumber": "Lap", "Lap time (s)": "Lap time (seconds)"},
        color_discrete_map={"Valid": "#45d6a8", "Missing time": "#9aa4b2", "Inaccurate": "#ffb454", "Deleted": "#ff5d73"},
    )
    figure.update_layout(height=460)
    return figure


def sector_chart(sectors: pd.DataFrame, driver: str | None = None):
    """Build a grouped sector comparison chart."""
    data = sectors.copy()
    if driver is not None and "Driver" in data:
        data = data[data["Driver"].eq(driver)]
    columns = [c for c in ("Best S1 (s)", "Best S2 (s)", "Best S3 (s)") if c in data]
    if data.empty or not columns:
        return px.bar(template="plotly_dark")
    long_data = data.melt(id_vars=["Driver"], value_vars=columns, var_name="Sector", value_name="Time (s)")
    figure = px.bar(long_data, x="Sector", y="Time (s)", color="Driver", barmode="group", template="plotly_dark")
    figure.update_layout(height=400)
    return figure


def tyre_strategy_chart(stints: pd.DataFrame, driver: str | None = None):
    """Build a horizontal observed-stint chart."""
    data = stints.copy()
    if driver is not None and "Driver" in data:
        data = data[data["Driver"].eq(driver)]
    if data.empty:
        return px.bar(template="plotly_dark")
    data["Start"] = data["Start lap"]
    data["Length"] = data["Stint length"]
    figure = px.bar(
        data,
        x="Length",
        y="Driver",
        base="Start",
        color="Compound",
        orientation="h",
        hover_data=["Stint", "Start lap", "End lap", "Fresh tyre"],
        template="plotly_dark",
        labels={"Length": "Observed stint length (laps)", "Driver": "Driver"},
        color_discrete_map={"SOFT": "#e74c3c", "MEDIUM": "#f4d03f", "HARD": "#e5e7eb", "INTERMEDIATE": "#39d353", "WET": "#3498db"},
    )
    figure.update_layout(height=max(420, min(900, 120 + 28 * data["Driver"].nunique())), xaxis_title="Lap", yaxis_title=None)
    return figure


def degradation_chart(data: pd.DataFrame, estimate: dict[str, object]):
    """Build observed tyre-life scatter with an optional calculated trend."""
    if data.empty:
        return px.scatter(template="plotly_dark")
    figure = px.scatter(data, x="Tyre life", y="Lap time (s)", hover_data=[c for c in ("LapNumber", "TrackStatus") if c in data], template="plotly_dark")
    if estimate.get("status") == "estimated":
        x_min, x_max = float(data["Tyre life"].min()), float(data["Tyre life"].max())
        slope = float(estimate["slope_seconds_per_lap"])
        intercept = float(estimate["intercept_seconds"])
        trend = pd.DataFrame({"Tyre life": [x_min, x_max], "Lap time (s)": [slope * x_min + intercept, slope * x_max + intercept]})
        figure.add_scatter(x=trend["Tyre life"], y=trend["Lap time (s)"], mode="lines", name="Observed trend")
    figure.update_layout(height=460, xaxis_title="Tyre life (laps)", yaxis_title="Lap time (seconds)")
    return figure


def pit_stop_chart(pits: pd.DataFrame):
    """Build a pit-stop marker timeline without implying pit duration."""
    if pits.empty:
        return px.scatter(template="plotly_dark")
    # FastF1/pandas may still provide nullable values when this chart is called
    # with a manually assembled or cached table. Normalize at the visualization
    # boundary so Plotly never receives pd.NA as a categorical value.
    safe = pits.copy()
    for column in ("Driver", "New compound", "Previous compound", "Evidence"):
        if column in safe:
            safe[column] = safe[column].astype("object").where(safe[column].notna(), "Unavailable").astype(str)
    return px.scatter(safe, x="Pit stop lap", y="Driver", color="New compound", hover_data=["Previous compound", "Evidence"], template="plotly_dark", height=max(380, 100 + 26 * safe["Driver"].nunique()))


def telemetry_chart(telemetry: pd.DataFrame, channel: str, title: str | None = None):
    """Build a telemetry channel chart against distance."""
    if telemetry is None or telemetry.empty or channel not in telemetry:
        return px.line(template="plotly_dark")
    figure = px.line(telemetry, x="Distance", y=channel, template="plotly_dark", labels={"Distance": "Distance (m)", channel: channel})
    figure.update_layout(height=360, title=title or f"{channel} vs distance")
    return figure


def telemetry_comparison_chart(driver_a: str, telemetry_a: pd.DataFrame, driver_b: str, telemetry_b: pd.DataFrame, channel: str):
    """Build a distance-aligned two-driver telemetry chart."""
    frames = []
    for driver, telemetry in ((driver_a, telemetry_a), (driver_b, telemetry_b)):
        if telemetry is not None and not telemetry.empty and channel in telemetry:
            part = telemetry[["Distance", channel]].copy()
            part["Driver"] = driver
            frames.append(part)
    if not frames:
        return px.line(template="plotly_dark")
    data = pd.concat(frames, ignore_index=True)
    return px.line(data, x="Distance", y=channel, color="Driver", template="plotly_dark", labels={"Distance": "Distance (m)", channel: channel}, title=f"{channel} comparison aligned by distance", height=360)


def weather_chart(weather: pd.DataFrame, channels: list[str]):
    """Build a weather trend chart for selected variables."""
    available = [column for column in channels if column in weather]
    if weather.empty or "Elapsed time (s)" not in weather or not available:
        return px.line(template="plotly_dark")
    data = weather[["Elapsed time (s)", *available]].melt(id_vars="Elapsed time (s)", var_name="Variable", value_name="Value").dropna()
    return px.line(data, x="Elapsed time (s)", y="Value", color="Variable", template="plotly_dark", labels={"Elapsed time (s)": "Session time (s)"}, height=430)


def timeline_chart(timeline: pd.DataFrame):
    """Build an event-oriented race timeline chart."""
    if timeline.empty:
        return px.scatter(template="plotly_dark")
    return px.scatter(timeline, x="Order", y="Event type", color="Event type", hover_data=["Lap", "Driver", "Details", "Status"], template="plotly_dark", labels={"Order": "Lap / relative event order"}, height=520)


def driver_comparison_lap_chart(data: pd.DataFrame):
    """Build same-lap-number comparison with a visible A-minus-B delta."""
    if data.empty:
        return px.line(template="plotly_dark")
    long = data.melt(id_vars="LapNumber", value_vars=[c for c in ("Driver A", "Driver B") if c in data], var_name="Driver", value_name="Lap time (s)")
    figure = px.line(long, x="LapNumber", y="Lap time (s)", color="Driver", template="plotly_dark", labels={"LapNumber": "Lap"}, markers=True)
    figure.update_layout(height=420)
    return figure


def speed_comparison_chart(laps: pd.DataFrame, drivers: list[str]):
    """Compare finish-line speed observations for selected drivers."""
    if laps.empty or "SpeedFL" not in laps or "LapNumber" not in laps:
        return px.line(template="plotly_dark")
    data = laps[laps["Driver"].isin(drivers)].copy()
    data["SpeedFL"] = pd.to_numeric(data["SpeedFL"], errors="coerce")
    data = data.dropna(subset=["LapNumber", "SpeedFL"])
    if data.empty:
        return px.line(template="plotly_dark")
    return px.line(data, x="LapNumber", y="SpeedFL", color="Driver", markers=True,
                   template="plotly_dark", labels={"LapNumber": "Lap", "SpeedFL": "Finish-line speed (km/h)"}, height=420)


def team_performance_chart(data: pd.DataFrame):
    """Build a team fastest-lap comparison."""
    if data.empty:
        return px.bar(template="plotly_dark")
    plot_data = data.copy()
    plot_data["Fastest lap (s)"] = pd.to_numeric(plot_data["Fastest lap"].astype(str).str.extract(r"([0-9]+(?:\.[0-9]+)?)")[0], errors="coerce")
    return px.bar(plot_data.sort_values("Fastest lap (s)", na_position="last"), x="Fastest lap (s)", y="Team", color="Points", orientation="h", template="plotly_dark", labels={"Fastest lap (s)": "Fastest lap (s)"}, height=max(420, 28 * len(plot_data)))
