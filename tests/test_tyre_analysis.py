import pandas as pd

from dashboard.charts import pit_stop_chart
from src.tyre_analysis import degradation_estimate, pit_stop_table, stint_table, tyre_life_data


def sample_tyre_laps():
    return pd.DataFrame(
        {
            "Driver": ["AAA", "AAA", "AAA", "AAA"],
            "Stint": [1, 1, 2, 2],
            "Compound": ["SOFT", "SOFT", "MEDIUM", "MEDIUM"],
            "LapNumber": [1, 2, 3, 4],
            "LapTime": [pd.Timedelta("90s"), pd.Timedelta("91s"), pd.Timedelta("92s"), pd.Timedelta("93s")],
            "TyreLife": [1, 2, 1, 2],
            "FreshTyre": [True, True, True, True],
            "IsAccurate": [True, True, True, True],
            "Deleted": [False, False, False, False],
            "PitInTime": [pd.NaT, pd.Timestamp("2026-01-01 00:02"), pd.NaT, pd.NaT],
            "PitOutTime": [pd.NaT, pd.NaT, pd.Timestamp("2026-01-01 00:03"), pd.NaT],
        }
    )


def test_stint_table_summarizes_observed_stints():
    result = stint_table(sample_tyre_laps())
    assert list(result["Compound"]) == ["SOFT", "MEDIUM"]
    assert result.iloc[0]["Stint length"] == 2


def test_degradation_estimate_requires_variation_and_returns_slope():
    data = pd.DataFrame({"Tyre life": [1, 2, 3], "Lap time (s)": [90.0, 91.0, 92.0]})
    result = degradation_estimate(data)
    assert result["status"] == "estimated"
    assert round(result["slope_seconds_per_lap"], 3) == 1.0


def test_pit_stop_table_uses_markers_without_duration():
    result = pit_stop_table(sample_tyre_laps())
    assert len(result) == 1
    assert result.iloc[0]["Previous compound"] == "SOFT"
    assert result.iloc[0]["New compound"] == "MEDIUM"
    assert pit_stop_chart(result) is not None


def test_pit_stop_chart_handles_nullable_categories_directly():
    raw = pd.DataFrame(
        {
            "Driver": ["AAA"],
            "Pit stop lap": [10],
            "New compound": [pd.NA],
            "Previous compound": ["SOFT"],
            "Evidence": ["PitInTime + following lap"],
        }
    )
    assert pit_stop_chart(raw) is not None


def test_tyre_life_data_filters_to_valid_driver_compound_laps():
    result = tyre_life_data(sample_tyre_laps(), "AAA", "SOFT")
    assert len(result) == 2
    assert list(result["Tyre life"]) == [1, 2]
