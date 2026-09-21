"""Streamlit entry point for the first analytical views."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.charts import degradation_chart, driver_comparison_lap_chart, lap_time_chart, pit_stop_chart, position_chart, sector_chart, speed_comparison_chart, team_performance_chart, telemetry_chart, telemetry_comparison_chart, timeline_chart, tyre_strategy_chart, weather_chart  # noqa: E402
from src.config import DEFAULT_SEASON  # noqa: E402
from src.data_processing import format_timedelta, get_fastest_lap, get_valid_laps  # noqa: E402
from src.driver_analysis import build_driver_summary, driver_lap_data, driver_options  # noqa: E402
from src.fastf1_loader import SessionLoadError, get_event_options, get_session_options, load_session  # noqa: E402
from src.lap_analysis import lap_statistics, quality_summary, sector_table  # noqa: E402
from src.telemetry_analysis import (  # noqa: E402
    TelemetryUnavailableError,
    get_lap_telemetry,
    resample_by_distance,
    telemetry_lap_options,
    telemetry_summary,
)
from src.race_events import build_race_timeline, clean_race_control_messages, clean_track_status  # noqa: E402
from src.weather_analysis import clean_weather, weather_summary  # noqa: E402
from src.team_analysis import comparison_lap_data, driver_comparison_table, team_options, team_performance_table, team_summary  # noqa: E402
from src.tyre_analysis import degradation_estimate, pit_stop_table, stint_table, tyre_life_data  # noqa: E402

st.set_page_config(page_title="F1 Analytics Hub", page_icon=":material/sports_motorsports:", layout="wide", initial_sidebar_state="auto")

st.markdown(
    """
    <style>
    .stApp { background: radial-gradient(circle at 82% -8%, #30242a 0, #10151c 34%, #0b0f14 72%); }
    .block-container { max-width: 1480px; padding: 2.25rem clamp(1rem, 3vw, 3.5rem) 4rem; }
    .hero-kicker, .page-eyebrow { color: #ff5a5f; font-size: 0.7rem; font-weight: 800; letter-spacing: 0.16rem; text-transform: uppercase; }
    .hero-kicker { margin-top: 1rem; }
    .page-eyebrow { margin-top: 1.75rem; margin-bottom: 0.35rem; }
    .landing-spacer { height: 1rem; }
    .landing-note { color: #9aa4b2; font-size: 0.82rem; margin-top: 1rem; }
    .session-chip { color: #aab4c2; font-size: 0.82rem; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #11161e 0%, #0d1218 100%); border-right: 1px solid #252d38; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.65rem; }
    [data-testid="stMetric"] { background: rgba(23, 29, 38, 0.76); border: 1px solid #2b3542; border-radius: 0.7rem; padding: 0.8rem 0.95rem; }
    [data-testid="stMetricLabel"] { color: #9aa7b7; font-size: 0.75rem; }
    [data-testid="stMetricValue"] { color: #f1f4f7; font-size: clamp(1.1rem, 2vw, 1.55rem); }
    [data-testid="stPlotlyChart"] { background: rgba(17, 22, 30, 0.55); border: 1px solid #252e3a; border-radius: 0.7rem; padding: 0.35rem; }
    div[data-testid="stDataFrame"] { border: 1px solid #252e3a; border-radius: 0.7rem; overflow: hidden; }
    .stButton > button { border-radius: 0.55rem; font-weight: 650; }
    @media (max-width: 640px) {
        .block-container { padding: 1.25rem 0.8rem 2.5rem; }
        .hero-kicker { margin-top: 0.25rem; }
        [data-testid="stMetric"] { padding: 0.65rem 0.7rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def cached_session(season: int, event: str, session_type: str):
    """Cache a loaded FastF1 session so widget reruns do not redownload it."""
    return load_session(season, event, session_type)


@st.cache_data(show_spinner=False, max_entries=64)
def cached_telemetry(season: int, event: str, session_type: str, driver: str, lap_number: int) -> pd.DataFrame:
    """Cache one selected lap's telemetry, not every lap in the session."""
    return get_lap_telemetry(cached_session(season, event, session_type), driver, lap_number)


@st.cache_data(ttl="1d", show_spinner=False, max_entries=20)
def cached_event_options(season: int) -> list[str]:
    """Cache the seasonal schedule used by the event selector."""
    return get_event_options(season)


@st.cache_data(ttl="1d", show_spinner=False, max_entries=100)
def cached_session_options(season: int, event: str) -> list[str]:
    """Cache the sessions available for the selected scheduled event."""
    return get_session_options(season, event)


def session_label(session) -> str:
    event = session.event
    name = event.get("EventName", "Selected event") if hasattr(event, "get") else "Selected event"
    return str(name)


def finishing_order(session) -> pd.DataFrame:
    """Prepare a compact finishing-order table from FastF1 results."""
    results = getattr(session, "results", pd.DataFrame()).copy()
    if results.empty:
        return results
    columns = [
        c for c in ("Position", "Abbreviation", "FullName", "TeamName", "GridPosition", "Status", "Points")
        if c in results
    ]
    return results[columns].sort_values("Position", na_position="last")


def classification_table(session) -> pd.DataFrame:
    """Combine FastF1 results with each driver's fastest valid lap."""
    results = finishing_order(session)
    if results.empty:
        return results
    fastest_rows = get_valid_laps(session.laps).sort_values("LapTime").drop_duplicates("Driver")
    fastest_columns = [c for c in ("Driver", "LapTime", "Compound", "LapNumber") if c in fastest_rows]
    if fastest_columns:
        fastest_rows = fastest_rows[fastest_columns].rename(columns={"Driver": "Abbreviation", "LapTime": "Fastest lap", "LapNumber": "Fastest lap number"})
        results = results.merge(fastest_rows, on="Abbreviation", how="left")
    rename = {"Abbreviation": "Driver", "TeamName": "Team", "GridPosition": "Grid", "Status": "Status", "Fastest lap": "Fastest lap"}
    table = results.rename(columns=rename)
    if "Fastest lap" in table:
        table["Fastest lap"] = table["Fastest lap"].map(format_timedelta)
    return table


def selected_session_date(session, session_type: str):
    """Read the date for the selected session from FastF1 event metadata."""
    event = session.event
    session_number = {"FP1": 1, "SQ": 2, "FP2": 2, "Sprint": 3, "FP3": 3, "Q": 4, "R": 5}.get(session_type)
    value = event.get(f"Session{session_number}Date", pd.NaT) if hasattr(event, "get") and session_number else pd.NaT
    return value


def page_heading(title: str, subtitle: str) -> None:
    """Render a consistent section heading across the dashboard."""
    st.markdown(f"<div class='page-eyebrow'>Performance view</div>", unsafe_allow_html=True)
    st.header(title)
    st.caption(subtitle)


def chart_section(title: str, figure, caption: str | None = None) -> None:
    """Render a chart as a consistent analytical card."""
    with st.container(border=True):
        st.subheader(title)
        st.plotly_chart(figure)
        if caption:
            st.caption(caption)


def format_lap_table(data: pd.DataFrame) -> pd.DataFrame:
    """Prepare user-facing lap columns without exposing Timedelta reprs."""
    result = data.copy()
    for column in ("LapTime", "Sector1Time", "Sector2Time", "Sector3Time"):
        if column in result:
            result[column] = result[column].map(format_timedelta)
    return result


SESSION_LABELS = {
    "FP1": "Practice 1",
    "FP2": "Practice 2",
    "FP3": "Practice 3",
    "Q": "Qualifying",
    "SQ": "Sprint qualifying",
    "Sprint": "Sprint",
    "R": "Race",
}

NAVIGATION = [
    "Overview",
    "Driver analysis",
    "Driver comparison",
    "Lap analysis",
    "Sector analysis",
    "Tyre strategy",
    "Tyre degradation",
    "Pit stops",
    "Telemetry",
    "Telemetry comparison",
    "Weather",
    "Race control",
    "Race timeline",
    "Teams",
    "Data quality",
]


def session_selection_page() -> None:
    """Render the empty-state landing page and explicit session selection."""
    load_error = st.session_state.pop("load_error", None)
    if load_error:
        st.error(load_error)
    st.markdown("<div class='hero-kicker'>MOTORSPORT · DATA · PERFORMANCE</div>", unsafe_allow_html=True)
    st.title("F1 Analytics Hub")
    st.markdown("## Understand the race beyond the result.")
    st.write("Explore Formula 1 performance, strategy, telemetry, weather and race events from real FastF1 data.")
    st.markdown("<div class='landing-spacer'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.subheader("Select a session")
        st.caption("Choose a season, Grand Prix and session. Data is loaded only after you press Load session.")
        season = st.selectbox("Season", list(range(2018, 2036)), index=list(range(2018, 2036)).index(DEFAULT_SEASON), key="landing_season")
        events = cached_event_options(int(season))
        if not events:
            st.warning("No FastF1 events are available for this season.")
            return
        event = st.selectbox("Grand Prix", events, index=None, placeholder="Select a Grand Prix", key="landing_event")
        sessions = cached_session_options(int(season), event) if event else []
        session_type = st.selectbox("Session", sessions, index=None, placeholder="Select a session", format_func=lambda code: SESSION_LABELS.get(code, code), key="landing_session", disabled=not bool(event))
        can_load = bool(event and session_type)
        if st.button("Load session", type="primary", disabled=not can_load, width="stretch"):
            st.session_state.loaded_session_key = (int(season), str(event), str(session_type))
            st.session_state.load_error = None
            st.rerun()
    st.markdown("<div class='landing-note'>Powered by FastF1 · Real-world Formula 1 timing, telemetry, tyre, weather and race-control data.</div>", unsafe_allow_html=True)


def dashboard_sidebar(selected: tuple[int, str, str]) -> str:
    """Render current-session context and the session reset action."""
    with st.sidebar:
        st.markdown("### :material/sports_motorsports: F1 Analytics Hub")
        st.caption("SESSION CONTEXT")
        with st.container(border=True):
            st.markdown(f"**{selected[1]}**")
            st.caption(f"{selected[0]} · {SESSION_LABELS.get(selected[2], selected[2])}")
        st.caption("WORKSPACE")
        page = st.selectbox("View", NAVIGATION, key="dashboard_page", label_visibility="collapsed")
        if st.button(":material/swap_horiz: Change session", width="stretch"):
            st.session_state.loaded_session_key = None
            st.rerun()
        st.caption("FastF1 data is cached locally after the first load.")
    return page


def overview_page(session, selected: tuple[int, str, str]) -> None:
    page_heading("Race overview", "What happened in the selected session, from the result to the race evolution.")
    laps = session.laps
    valid_laps = get_valid_laps(laps)
    fastest = get_fastest_lap(laps)
    event_info = session.event
    results = getattr(session, "results", pd.DataFrame())
    ordered_results = results.sort_values("Position", na_position="last") if not results.empty and "Position" in results else results
    fastest_driver = fastest.get("Driver", "—") if fastest is not None else "—"
    circuit = event_info.get("Location", "—") if hasattr(event_info, "get") else "—"

    with st.container(horizontal=True):
        st.metric("Grand Prix", session_label(session), border=True)
        st.metric("Circuit", str(circuit), border=True)
        st.metric("Fastest driver", str(fastest_driver), border=True)
        st.metric("Valid laps", f"{len(valid_laps):,}", border=True)
    st.subheader("Podium")
    with st.container(horizontal=True):
        for index, label in enumerate(("Winner", "P2", "P3")):
            driver = ordered_results.iloc[index].get("Abbreviation", "—") if len(ordered_results) > index else "—"
            st.metric(label, str(driver), border=True)
    session_date = selected_session_date(session, selected[2])
    with st.container(horizontal=True):
        st.metric("Date", str(session_date.date()) if pd.notna(session_date) else "—", border=True)
        st.metric("Total laps", str(int(laps["LapNumber"].max())) if "LapNumber" in laps and laps["LapNumber"].notna().any() else "—", border=True)
        st.metric("Drivers", str(laps["Driver"].nunique()) if "Driver" in laps else "—", border=True)

    if fastest is not None:
        st.subheader("Fastest valid lap")
        st.info(f"{fastest.get('Driver', '—')} · {format_timedelta(fastest.get('LapTime', pd.NaT))} · {fastest.get('Compound', 'Unavailable')} · lap {fastest.get('LapNumber', '—')}")

    st.subheader("Race classification")
    order = classification_table(session)
    if order.empty:
        st.info("Finishing-order data is unavailable for this session.")
    else:
        st.dataframe(order, hide_index=True)

    if all(column in laps for column in ("LapNumber", "Position", "Driver")):
        chart_section("Race position progression", position_chart(laps), "Lower values indicate a better race position.")
    else:
        st.warning("Position data is unavailable for this session.")

    with st.expander("Session metadata"):
        st.table({
            "Season": str(selected[0]),
            "Event": str(selected[1]),
            "Session": str(selected[2]),
            "Raw lap records": f"{len(laps):,}",
            "Drivers with lap records": f"{int(laps['Driver'].nunique()) if 'Driver' in laps else 0:,}",
        })


def driver_page(session) -> None:
    page_heading("Driver analysis", "Explore one driver's pace, position, sectors, and data coverage.")
    laps = session.laps
    options = driver_options(laps)
    if not options:
        st.warning("No driver lap data is available.")
        return
    driver = st.selectbox("Driver", options, key="driver_analysis_driver")
    summary = build_driver_summary(laps, getattr(session, "results", pd.DataFrame()), driver)
    with st.container(horizontal=True):
        for label in ("Driver", "Team", "Position", "Grid", "Points"):
            st.metric(label, str(summary.get(label, "—")), border=True)
    with st.container(horizontal=True):
        for label in ("Fastest lap", "Average lap", "Valid laps", "Best finish-line speed", "Compounds"):
            st.metric(label, str(summary.get(label, "—")), border=True)

    driver_laps = driver_lap_data(laps, driver)
    chart_section(f"{driver} lap performance", lap_time_chart(driver_laps, driver), "Valid, missing, inaccurate, and deleted observations use distinct colors.")

    position_data = driver_laps.dropna(subset=["LapNumber", "Position"]) if "Position" in driver_laps else pd.DataFrame()
    if not position_data.empty:
        st.subheader("Position progression")
        st.line_chart(position_data.set_index("LapNumber"), y="Position")

    sectors = sector_table(laps)
    if not sectors.empty:
        chart_section("Sector performance", sector_chart(sectors, driver), "Theoretical best combines each sector's best observed lap. It is not necessarily an actual lap.")

    visible = [c for c in ("LapNumber", "LapTime", "Compound", "TyreLife", "Position", "TrackStatus", "Validity") if c in driver_laps]
    st.dataframe(format_lap_table(driver_laps[visible].sort_values("LapNumber")), hide_index=True)


def driver_comparison_page(session) -> None:
    """Compare two drivers on valid lap, sector, speed, and progression metrics."""
    page_heading("Driver comparison", "Compare two drivers using valid observations from the same session.")
    drivers = driver_options(session.laps)
    if len(drivers) < 2:
        st.warning("At least two drivers are required for comparison.")
        return
    left, right = st.columns(2)
    with left:
        driver_a = st.selectbox("Driver A", drivers, index=0, key="comparison_driver_a")
    with right:
        driver_b = st.selectbox("Driver B", drivers, index=1, key="comparison_driver_b")
    if driver_a == driver_b:
        st.info("Choose two different drivers to calculate a meaningful delta.")
        return
    comparison = driver_comparison_table(session.laps, getattr(session, "results", pd.DataFrame()), driver_a, driver_b)
    metric_columns = [c for c in ("Fastest lap (s)", "Average lap (s)", "Best S1 (s)", "Best S2 (s)", "Best S3 (s)", "Top speed (km/h)", "Valid laps") if c in comparison]
    for metric in metric_columns:
        row = comparison.set_index("Driver")
        a_value = row.loc[driver_a, metric] if driver_a in row.index else None
        b_value = row.loc[driver_b, metric] if driver_b in row.index else None
        if "lap" in metric.lower() and "(s)" in metric:
            a_value = format_timedelta(pd.Timedelta(seconds=float(a_value))) if pd.notna(a_value) else "—"
            b_value = format_timedelta(pd.Timedelta(seconds=float(b_value))) if pd.notna(b_value) else "—"
        with st.container(horizontal=True):
            st.metric(f"{driver_a} · {metric}", str(a_value) if pd.notna(a_value) else "—", border=True)
            st.metric(f"{driver_b} · {metric}", str(b_value) if pd.notna(b_value) else "—", border=True)
    comparison_table = comparison.copy()
    for column in ("Fastest lap (s)", "Average lap (s)"):
        if column in comparison_table:
            comparison_table[column] = comparison_table[column].map(lambda value: format_timedelta(pd.Timedelta(seconds=float(value))) if pd.notna(value) else "—")
    st.dataframe(comparison_table, hide_index=True)
    st.caption("Delta convention: Driver A minus Driver B. Negative values mean Driver A was faster for that metric.")
    lap_data = comparison_lap_data(session.laps, driver_a, driver_b)
    chart_section("Lap-time comparison", driver_comparison_lap_chart(lap_data), "Same-lap-number comparison; gaps are shown below as Driver A minus Driver B.")
    if not lap_data.empty and "Delta A - B (s)" in lap_data:
        st.line_chart(lap_data.set_index("LapNumber"), y="Delta A - B (s)")
    comparison_laps = session.laps[session.laps["Driver"].isin([driver_a, driver_b])] if "Driver" in session.laps else pd.DataFrame()
    if {"LapNumber", "Position", "Driver"}.issubset(comparison_laps.columns):
        chart_section("Position comparison", position_chart(comparison_laps), "Lower values indicate a better race position.")
    else:
        st.info("Position observations are unavailable for this comparison.")
    chart_section("Finish-line speed comparison", speed_comparison_chart(comparison_laps, [driver_a, driver_b]))
    comparison_stints = stint_table(comparison_laps)
    if comparison_stints.empty:
        st.info("Tyre stint data is unavailable for these drivers.")
    else:
        chart_section("Tyre strategy comparison", tyre_strategy_chart(comparison_stints))


def team_page(session) -> None:
    """Display team-level performance and teammate comparison."""
    page_heading("Team analysis", "Compare team-level pace, points, speed, and teammate performance.")
    results = getattr(session, "results", pd.DataFrame())
    teams = team_options(results, session.laps)
    if not teams:
        st.warning("No team data is available for this session.")
        return
    team = st.selectbox("Team", teams, key="team_analysis_team")
    summary = team_summary(session.laps, results, team)
    with st.container(horizontal=True):
        for label in ("Team", "Drivers", "Points", "Fastest lap", "Average lap", "Top speed"):
            value = summary.get(label, "—")
            if label in ("Fastest lap", "Average lap") and pd.notna(value):
                seconds = pd.to_numeric(pd.Series([str(value)]).str.extract(r"([0-9]+(?:\.[0-9]+)?)")[0], errors="coerce").iloc[0]
                value = format_timedelta(pd.Timedelta(seconds=float(seconds))) if pd.notna(seconds) else "—"
            st.metric(label, str(value), border=True)
    team_table = team_performance_table(session.laps, results)
    chart_section("Team performance comparison", team_performance_chart(team_table.rename(columns={"Fastest lap": "Fastest lap"})))
    st.dataframe(team_table, hide_index=True)
    team_drivers = results.loc[results["TeamName"].eq(team), "Abbreviation"].dropna().astype(str).tolist() if "TeamName" in results and "Abbreviation" in results else []
    if len(team_drivers) >= 2:
        teammate_data = comparison_lap_data(session.laps, team_drivers[0], team_drivers[1])
        chart_section("Teammate lap comparison", driver_comparison_lap_chart(teammate_data))
    else:
        st.info("A teammate comparison is unavailable because fewer than two result drivers are present.")
    team_laps = session.laps[session.laps["Team"].eq(team)] if "Team" in session.laps else pd.DataFrame()
    team_sectors = sector_table(team_laps)
    if not team_sectors.empty:
        chart_section("Team sector performance", sector_chart(team_sectors))
    team_stints = stint_table(team_laps)
    if not team_stints.empty:
        chart_section("Team tyre strategy", tyre_strategy_chart(team_stints))


def lap_page(session) -> None:
    page_heading("Lap analysis", "Inspect lap evolution while keeping deleted and inaccurate records visible.")
    laps = session.laps
    options = driver_options(laps)
    if not options:
        st.warning("No driver lap data is available.")
        return
    driver = st.selectbox("Driver", options, key="lap_analysis_driver")
    driver_laps = driver_lap_data(laps, driver)
    if driver_laps.empty:
        st.info("No lap records are available for this driver.")
        return
    min_lap = int(driver_laps["LapNumber"].min()) if driver_laps["LapNumber"].notna().any() else 1
    max_lap = int(driver_laps["LapNumber"].max()) if driver_laps["LapNumber"].notna().any() else min_lap
    selected_range = st.slider("Lap range", min_lap, max_lap, (min_lap, max_lap))
    filtered = driver_laps[driver_laps["LapNumber"].between(*selected_range)]
    compound_options = ["All compounds", *sorted(driver_laps["Compound"].dropna().astype(str).unique())] if "Compound" in driver_laps else ["All compounds"]
    selected_compound = st.selectbox("Compound", compound_options, key="lap_analysis_compound")
    if selected_compound != "All compounds" and "Compound" in filtered:
        filtered = filtered[filtered["Compound"].astype(str).eq(selected_compound)]
    stats = lap_statistics(filtered)
    with st.container(horizontal=True):
        for label, value in stats.items():
            st.metric(label, value, border=True)
    chart_section(f"{driver} lap times", lap_time_chart(filtered, driver), "Statistics use valid lap times only; the table retains the selected data-quality context.")
    columns = [c for c in ("LapNumber", "LapTime", "Compound", "TyreLife", "Position", "Sector1Time", "Sector2Time", "Sector3Time", "TrackStatus", "Validity") if c in filtered]
    st.dataframe(format_lap_table(filtered[columns].sort_values("LapNumber")), hide_index=True)
    st.caption("Statistics use valid lap times only. The chart retains missing, inaccurate, and deleted records so data-quality issues remain visible.")


def sector_page(session) -> None:
    page_heading("Sector analysis", "Compare best observed sectors and theoretical combinations.")
    sectors = sector_table(session.laps)
    if sectors.empty:
        st.warning("Sector timing data is unavailable for this session.")
        return
    st.subheader("Best sector times")
    st.dataframe(sectors.sort_values("Theoretical best (s)"), hide_index=True)
    chart_section("Sector comparison", sector_chart(sectors))
    st.info("The theoretical best lap is a calculated combination of a driver's best S1, S2, and S3 from potentially different laps. It should not be interpreted as an observed lap time.")


def quality_page(session) -> None:
    page_heading("Data quality", "Engineering data-quality indicators for the selected FastF1 feed.")
    quality = quality_summary(session.laps)
    with st.container(horizontal=True):
        for label, value in quality.items():
            st.metric(label, f"{value:,}", border=True)
    telemetry_feed = getattr(session, "car_data", pd.DataFrame())
    weather_feed = getattr(session, "weather_data", pd.DataFrame())
    with st.container(horizontal=True):
        telemetry_count = sum(len(value) for value in telemetry_feed.values()) if isinstance(telemetry_feed, dict) else (len(telemetry_feed) if hasattr(telemetry_feed, "__len__") else None)
        st.metric("Telemetry records", f"{telemetry_count:,}" if telemetry_count is not None else "Unavailable", border=True)
        st.metric("Weather records", f"{len(weather_feed):,}" if hasattr(weather_feed, "__len__") else "Unavailable", border=True)
        st.metric("Drivers assessed", f"{session.laps['Driver'].nunique():,}" if "Driver" in session.laps else "—", border=True)
    st.warning("Real timing feeds can contain missing, deleted, or inaccurate records. Filtering is explicit and raw records remain available for inspection.")
    if "Driver" in session.laps:
        by_driver = session.laps.groupby("Driver", dropna=False).size().reset_index(name="Raw records")
        by_driver["Max lap"] = session.laps.groupby("Driver")["LapNumber"].max().reindex(by_driver["Driver"]).to_numpy() if "LapNumber" in session.laps else pd.NA
        st.metric("Drivers with incomplete distance", f"{int((by_driver['Max lap'] < by_driver['Max lap'].max()).sum()):,}" if "Max lap" in by_driver else "—", border=True)
        st.subheader("Raw records by driver")
        st.dataframe(by_driver.sort_values("Raw records", ascending=False), hide_index=True)


def tyre_strategy_page(session) -> None:
    """Display observed compound stints for all drivers or one driver."""
    page_heading("Tyre strategy", "See how each driver used compounds across observed stints.")
    stints = stint_table(session.laps)
    if stints.empty:
        st.warning("Tyre stint data is unavailable for this session.")
        return
    drivers = ["All drivers", *sorted(stints["Driver"].unique())]
    selected_driver = st.selectbox("Driver", drivers, key="tyre_strategy_driver")
    driver_filter = None if selected_driver == "All drivers" else selected_driver
    chart_section("Observed stint strategy", tyre_strategy_chart(stints, driver_filter), "Compound colors follow the standard F1 tyre palette.")
    visible = [c for c in ("Driver", "Stint", "Compound", "Start lap", "End lap", "Stint length", "Fresh tyre", "Average lap (s)", "Best lap (s)") if c in stints]
    visible_table = stints[visible].copy()
    for column in ("Average lap (s)", "Best lap (s)"):
        if column in visible_table:
            visible_table[column] = visible_table[column].map(lambda value: format_timedelta(pd.Timedelta(seconds=float(value))) if pd.notna(value) else "—")
    st.dataframe(visible_table, hide_index=True)
    st.caption("Stints use FastF1's reported stint, compound, and observed lap numbers. Missing laps between records are not inferred.")


def degradation_page(session) -> None:
    """Explore observed lap time against tyre life for one driver and compound."""
    page_heading("Tyre degradation", "Observed lap-time trend against tyre life; not a causal degradation model.")
    stints = stint_table(session.laps)
    if stints.empty:
        st.warning("Tyre data is unavailable for this session.")
        return
    drivers = sorted(stints["Driver"].unique())
    driver = st.selectbox("Driver", drivers, key="degradation_driver")
    compounds = sorted(stints.loc[stints["Driver"].eq(driver), "Compound"].unique())
    compound = st.selectbox("Compound", compounds, key="degradation_compound")
    data = tyre_life_data(session.laps, driver, compound)
    estimate = degradation_estimate(data)
    chart_section(f"{driver} · {compound} tyre life", degradation_chart(data, estimate), "This is an observed association, not a causal degradation model.")
    if estimate.get("status") == "estimated":
        st.metric("Observed trend", f"{float(estimate['slope_seconds_per_lap']):+.3f} s/lap", border=True)
        st.caption(f"Calculated from {estimate['points']} valid laps; R² = {float(estimate['r_squared']):.3f}. This is an observed association, not a causal degradation model.")
    else:
        st.info(f"Trend unavailable: {estimate.get('status')} ({estimate.get('points', 0)} usable points).")
    st.dataframe(data[[c for c in ("LapNumber", "Tyre life", "Lap time (s)", "TrackStatus") if c in data]], hide_index=True)


def pit_stop_page(session) -> None:
    """Show pit-in/pit-out evidence without fabricating pit-lane duration."""
    page_heading("Pit stops", "Pit-in and pit-out evidence from the timing feed, without invented durations.")
    pits = pit_stop_table(session.laps)
    if pits.empty:
        st.info("No reliable pit-in or pit-out markers were found in this session.")
        return
    chart_section("Pit-stop timeline", pit_stop_chart(pits), "Markers show pit-in/pit-out evidence; no unsupported pit-lane duration is inferred.")
    st.dataframe(pits, hide_index=True)
    st.caption("Exact pit-stop duration is intentionally omitted because the available timing markers do not guarantee a reliable entry-to-exit interval.")


def telemetry_page(session, selected: tuple[int, str, str]) -> None:
    """Display one driver's telemetry for a selected lap."""
    page_heading("Telemetry", "Inspect sampled car data against distance for one driver and lap.")
    drivers = driver_options(session.laps)
    if not drivers:
        st.warning("No drivers are available for telemetry analysis.")
        return
    driver = st.selectbox("Driver", drivers, key="telemetry_driver")
    laps = telemetry_lap_options(session.laps, driver)
    if not laps:
        st.info(f"No usable lap records are available for {driver}.")
        return
    lap_number = st.selectbox("Lap", laps, index=len(laps) - 1, key="telemetry_lap")
    try:
        telemetry = cached_telemetry(*selected, driver, int(lap_number))
    except TelemetryUnavailableError as exc:
        st.warning(str(exc))
        st.info("Telemetry availability varies by session and lap. Try another lap or session.")
        return

    summary = telemetry_summary(telemetry)
    summary_items = list(summary.items())
    for start in range(0, len(summary_items), 4):
        with st.container(horizontal=True):
            for label, value in summary_items[start:start + 4]:
                st.metric(label, str(value), border=True)
    st.caption("Telemetry is sampled from the car data feed. Distance is used as the horizontal axis because samples are not evenly spaced in time.")

    tabs = st.tabs(["Speed", "Throttle", "Brake", "RPM", "Gear"])
    for tab, label, channel in zip(tabs, ["Speed", "Throttle", "Brake", "RPM", "Gear"], ["Speed", "Throttle", "Brake", "RPM", "nGear"]):
        with tab:
            chart_section(f"{driver} lap {lap_number} · {label}", telemetry_chart(telemetry, channel, f"{driver} lap {lap_number}: {label}"))
    visible = [c for c in ("Distance", "Speed", "Throttle", "Brake", "RPM", "nGear", "DRS", "DriverAhead") if c in telemetry]
    st.dataframe(telemetry[visible].head(500), hide_index=True)


def telemetry_comparison_page(session, selected: tuple[int, str, str]) -> None:
    """Compare two laps after interpolating both telemetry streams by distance."""
    page_heading("Telemetry comparison", "Compare two telemetry streams aligned to the same track distance.")
    drivers = driver_options(session.laps)
    if len(drivers) < 2:
        st.warning("At least two drivers are required for telemetry comparison.")
        return
    first, second = st.columns(2)
    with first:
        driver_a = st.selectbox("Driver A", drivers, index=0, key="telemetry_compare_driver_a")
        laps_a = telemetry_lap_options(session.laps, driver_a)
        lap_a = st.selectbox("Driver A lap", laps_a, index=len(laps_a) - 1, key="telemetry_compare_lap_a") if laps_a else None
    with second:
        driver_b = st.selectbox("Driver B", drivers, index=1, key="telemetry_compare_driver_b")
        laps_b = telemetry_lap_options(session.laps, driver_b)
        lap_b = st.selectbox("Driver B lap", laps_b, index=len(laps_b) - 1, key="telemetry_compare_lap_b") if laps_b else None
    if lap_a is None or lap_b is None:
        st.info("Both drivers need at least one usable lap with telemetry.")
        return
    try:
        telemetry_a = resample_by_distance(cached_telemetry(*selected, driver_a, int(lap_a)))
        telemetry_b = resample_by_distance(cached_telemetry(*selected, driver_b, int(lap_b)))
    except TelemetryUnavailableError as exc:
        st.warning(str(exc))
        return
    st.info("The comparison is aligned by distance rather than timestamp. This compares the cars at comparable track locations despite unequal telemetry sampling times and lengths.")
    tabs = st.tabs(["Speed", "Throttle", "Brake", "RPM", "Gear"])
    for tab, label, channel in zip(tabs, ["Speed", "Throttle", "Brake", "RPM", "Gear"], ["Speed", "Throttle", "Brake", "RPM", "nGear"]):
        with tab:
            chart_section(f"{label} comparison", telemetry_comparison_chart(driver_a, telemetry_a, driver_b, telemetry_b, channel))


def weather_page(session) -> None:
    """Display observed weather channels and ranges."""
    page_heading("Weather", "Observed session conditions from FastF1 weather data.")
    weather = clean_weather(getattr(session, "weather_data", pd.DataFrame()))
    if weather.empty:
        st.info("Weather data is unavailable for this session.")
        return
    summary = weather_summary(weather)
    with st.container(horizontal=True):
        for label, value in summary.items():
            st.metric(label, str(value), border=True)
    variables = st.multiselect("Weather variables", ["AirTemp", "TrackTemp", "Humidity", "Pressure", "WindSpeed", "WindDirection"], default=["AirTemp", "TrackTemp"], key="weather_variables")
    chart_section("Weather trend", weather_chart(weather, variables), "Only observed FastF1 weather values are shown; missing variables are not interpolated.")
    display_columns = [c for c in ("Time", "Elapsed time (s)", "AirTemp", "TrackTemp", "Humidity", "Pressure", "Rainfall", "WindDirection", "WindSpeed") if c in weather]
    st.dataframe(weather[display_columns], hide_index=True)
    st.caption("Only observed FastF1 weather values are shown. Missing variables are not interpolated or fabricated.")


def events_page(session) -> None:
    """Display race-control messages and track-status intervals."""
    page_heading("Race control", "Flags, incidents, and track-status messages reported by the session feed.")
    messages = clean_race_control_messages(getattr(session, "race_control_messages", pd.DataFrame()))
    status = clean_track_status(getattr(session, "track_status", pd.DataFrame()))
    tabs = st.tabs(["Race control", "Track status"])
    with tabs[0]:
        if messages.empty:
            st.info("Race-control messages are unavailable for this session.")
        else:
            text = messages.astype(str).agg(" ".join, axis=1).str.upper()
            filter_options = ["All", "Flags", "Safety car", "VSC", "Penalties", "Other"]
            selected_filter = st.selectbox("Focus", filter_options, key="event_focus")
            if selected_filter == "All":
                focus_mask = pd.Series(True, index=messages.index)
            elif selected_filter == "Flags":
                focus_mask = text.str.contains("FLAG|YELLOW|RED|GREEN|BLUE|CHEQUERED", regex=True)
            elif selected_filter == "Safety car":
                focus_mask = text.str.contains("SAFETY CAR|SCDEPLOYED|SCENDING", regex=True)
            elif selected_filter == "VSC":
                focus_mask = text.str.contains("VSC", regex=True)
            elif selected_filter == "Penalties":
                focus_mask = text.str.contains("PENAL|INFRINGEMENT|INVESTIGAT", regex=True)
            else:
                focus_mask = ~(text.str.contains("FLAG|YELLOW|RED|GREEN|BLUE|CHEQUERED|SAFETY CAR|SCDEPLOYED|SCENDING|VSC|PENAL|INFRINGEMENT|INVESTIGAT", regex=True))
            categories = sorted(messages["Category"].unique()) if "Category" in messages else []
            selected_categories = st.multiselect("Message categories", categories, default=categories, key="event_categories")
            filtered = messages[focus_mask & messages["Category"].isin(selected_categories)] if selected_categories else messages.iloc[0:0]
            st.dataframe(filtered, hide_index=True)
    with tabs[1]:
        if status.empty:
            st.info("Track-status data is unavailable for this session.")
        else:
            st.dataframe(status, hide_index=True)
            st.caption("FastF1 status examples include AllClear, Yellow, SCDeployed, Red, VSCDeployed, and VSCEnding. Interpretations are preserved from the source feed.")


def timeline_page(session) -> None:
    """Combine lap, tyre, pit, track-status, and race-control observations."""
    page_heading("Race timeline", "A unified exploratory sequence of laps, strategy, pits, status, and race control.")
    timeline = build_race_timeline(
        session.laps,
        stint_table(session.laps),
        pit_stop_table(session.laps),
        getattr(session, "track_status", pd.DataFrame()),
        getattr(session, "race_control_messages", pd.DataFrame()),
    )
    if timeline.empty:
        st.info("No timeline events are available for this session.")
        return
    event_types = sorted(timeline["Event type"].unique())
    selected_types = st.multiselect("Timeline event types", event_types, default=event_types, key="timeline_event_types")
    filtered = timeline[timeline["Event type"].isin(selected_types)]
    chart_section("Event sequence", timeline_chart(filtered), "Events are ordered using observed lap numbers where available; timestamp-only events use relative session time.")
    st.dataframe(filtered, hide_index=True)
    st.caption("Events are ordered using observed lap numbers where available; timestamp-only events use relative session time converted to a timeline order. This is an exploratory event sequence, not an inferred causal model.")


def render_view(page: str, session, selected: tuple[int, str, str]) -> None:
    """Dispatch one analytical view behind a shared loading boundary."""
    if page == "Driver analysis":
        driver_page(session)
    elif page == "Driver comparison":
        driver_comparison_page(session)
    elif page == "Lap analysis":
        lap_page(session)
    elif page == "Sector analysis":
        sector_page(session)
    elif page == "Tyre strategy":
        tyre_strategy_page(session)
    elif page == "Tyre degradation":
        degradation_page(session)
    elif page == "Pit stops":
        pit_stop_page(session)
    elif page == "Telemetry":
        telemetry_page(session, selected)
    elif page == "Telemetry comparison":
        telemetry_comparison_page(session, selected)
    elif page == "Weather":
        weather_page(session)
    elif page == "Race control":
        events_page(session)
    elif page == "Race timeline":
        timeline_page(session)
    elif page == "Teams":
        team_page(session)
    elif page == "Data quality":
        quality_page(session)
    else:
        overview_page(session, selected)


def loaded_dashboard(selected: tuple[int, str, str]) -> None:
    """Render the dashboard only after the user explicitly loads a session."""
    page = dashboard_sidebar(selected)
    with st.spinner(f"Loading Formula 1 data for {selected[1]} — {SESSION_LABELS.get(selected[2], selected[2])}..."):
        try:
            session = cached_session(*selected)
        except SessionLoadError as exc:
            st.session_state.loaded_session_key = None
            st.session_state.load_error = str(exc)
            st.rerun()
    with st.container(horizontal=True, vertical_alignment="bottom"):
        st.markdown(f"### {session_label(session)}")
        st.caption(f"{selected[0]} · {SESSION_LABELS.get(selected[2], selected[2])} · FastF1-powered analysis")
        st.badge("Loaded", icon=":material/check_circle:", color="green")
    with st.spinner(f"Preparing {page.lower()}…"):
        render_view(page, session, selected)


if "loaded_session_key" not in st.session_state:
    st.session_state.loaded_session_key = None

if st.session_state.loaded_session_key is None:
    session_selection_page()
else:
    loaded_dashboard(st.session_state.loaded_session_key)
