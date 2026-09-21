import pandas as pd

from src.race_events import build_race_timeline, clean_race_control_messages, clean_track_status
from src.weather_analysis import clean_weather, weather_summary


def test_weather_cleaning_and_summary():
    weather = pd.DataFrame({"Time": [pd.Timedelta(seconds=0), pd.Timedelta(seconds=60)], "AirTemp": [30.0, 31.0], "TrackTemp": [50.0, 52.0], "Rainfall": [False, True]})
    cleaned = clean_weather(weather)
    assert cleaned.iloc[-1]["Elapsed time (s)"] == 60
    assert weather_summary(weather)["Rain samples"] == 1


def test_event_cleaning_preserves_missing_messages_as_text():
    messages = clean_race_control_messages(pd.DataFrame({"Time": [pd.Timestamp("2026-01-01")], "Category": ["Flag"], "Message": [pd.NA], "Lap": [1]}))
    status = clean_track_status(pd.DataFrame({"Time": [pd.Timedelta(seconds=5)], "Status": [2], "Message": ["Yellow"]}))
    assert messages.iloc[0]["Message"] == "Unavailable"
    assert status.iloc[0]["Status"] == "2"


def test_timeline_combines_event_sources():
    laps = pd.DataFrame({"LapNumber": [1], "Driver": ["AAA"], "Position": [1]})
    stints = pd.DataFrame(columns=["Stint", "Start lap", "Driver", "Compound"])
    pits = pd.DataFrame(columns=["Pit stop lap", "Driver", "Previous compound", "New compound", "Evidence"])
    track = pd.DataFrame({"Time": [pd.Timedelta(seconds=5)], "Status": ["Yellow"], "Message": ["Yellow"]})
    control = pd.DataFrame({"Time": [pd.Timestamp("2026-01-01")], "Category": ["Flag"], "Message": ["GREEN"], "Lap": [1]})
    result = build_race_timeline(laps, stints, pits, track, control)
    assert set(result["Event type"]) == {"Lap", "Track status", "Race control"}

