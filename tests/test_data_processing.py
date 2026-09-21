import pandas as pd

from src.data_processing import calculate_average_lap, get_fastest_lap, get_valid_laps


def sample_laps():
    return pd.DataFrame(
        {
            "Driver": ["AAA", "AAA", "BBB"],
            "LapTime": [pd.Timedelta(seconds=90), pd.NaT, pd.Timedelta(seconds=91)],
            "IsAccurate": [True, True, False],
            "Deleted": [False, False, False],
        }
    )


def test_valid_laps_exclude_missing_inaccurate_records():
    assert len(get_valid_laps(sample_laps())) == 1


def test_fastest_lap_returns_record():
    fastest = get_fastest_lap(sample_laps())
    assert fastest is not None
    assert fastest["Driver"] == "AAA"


def test_average_returns_none_for_empty_input():
    assert calculate_average_lap(pd.DataFrame()) is None

