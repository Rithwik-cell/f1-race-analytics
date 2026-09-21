import pandas as pd

from src.data_processing import calculate_sector_statistics, get_driver_laps


def test_driver_filter_preserves_driver_records():
    laps = pd.DataFrame({"Driver": ["AAA", "BBB"], "LapTime": [pd.Timedelta(seconds=90), pd.Timedelta(seconds=91)]})
    assert len(get_driver_laps(laps, "AAA")) == 1


def test_sector_minimums_are_grouped_by_driver():
    laps = pd.DataFrame(
        {
            "Driver": ["AAA", "AAA"],
            "LapTime": [pd.Timedelta(seconds=90), pd.Timedelta(seconds=91)],
            "Sector1Time": [pd.Timedelta(seconds=30), pd.Timedelta(seconds=29)],
        }
    )
    result = calculate_sector_statistics(laps)
    assert result.iloc[0]["Sector1Time"] == pd.Timedelta(seconds=29)

