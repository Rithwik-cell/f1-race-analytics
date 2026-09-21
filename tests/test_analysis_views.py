import pandas as pd

from src.lap_analysis import lap_statistics, quality_summary, sector_table


def test_lap_statistics_use_valid_records_only():
    laps = pd.DataFrame(
        {
            "LapTime": [pd.Timedelta("90s"), pd.Timedelta("91s"), pd.NaT],
            "IsAccurate": [True, False, True],
            "Deleted": [False, False, False],
        }
    )
    stats = lap_statistics(laps)
    assert stats["Minimum"] == "90.000 s"
    assert stats["Maximum"] == "90.000 s"


def test_sector_table_calculates_theoretical_best():
    laps = pd.DataFrame(
        {
            "Driver": ["AAA", "AAA"],
            "LapTime": [pd.Timedelta("90s"), pd.Timedelta("91s")],
            "Sector1Time": [pd.Timedelta("30s"), pd.Timedelta("29s")],
            "Sector2Time": [pd.Timedelta("30s"), pd.Timedelta("31s")],
            "Sector3Time": [pd.Timedelta("30s"), pd.Timedelta("30s")],
        }
    )
    result = sector_table(laps)
    assert result.iloc[0]["Theoretical best (s)"] == 89


def test_quality_summary_counts_explicit_flags():
    laps = pd.DataFrame(
        {
            "LapTime": [pd.Timedelta("90s"), pd.NaT],
            "IsAccurate": [True, False],
            "Deleted": [False, True],
        }
    )
    assert quality_summary(laps) == {
        "Raw records": 2,
        "Valid records": 1,
        "Missing lap times": 1,
        "Deleted laps": 1,
        "Inaccurate laps": 1,
    }

