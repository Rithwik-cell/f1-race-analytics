import pandas as pd

from src.team_analysis import comparison_lap_data, driver_comparison_table, team_performance_table


def sample_team_data():
    laps = pd.DataFrame({
        "Driver": ["AAA", "AAA", "BBB", "BBB"],
        "Team": ["Team X"] * 4,
        "LapNumber": [1, 2, 1, 2],
        "LapTime": [pd.Timedelta("90s"), pd.Timedelta("91s"), pd.Timedelta("92s"), pd.Timedelta("93s")],
        "IsAccurate": [True] * 4,
        "Deleted": [False] * 4,
        "SpeedFL": [300, 301, 302, 303],
        "Sector1Time": [pd.Timedelta("30s")] * 4,
        "Sector2Time": [pd.Timedelta("30s")] * 4,
        "Sector3Time": [pd.Timedelta("30s")] * 4,
    })
    results = pd.DataFrame({"Abbreviation": ["AAA", "BBB"], "TeamName": ["Team X", "Team X"], "Points": [10, 8]})
    return laps, results


def test_team_performance_table_and_driver_comparison():
    laps, results = sample_team_data()
    assert team_performance_table(laps, results).iloc[0]["Points"] == 18
    assert len(driver_comparison_table(laps, results, "AAA", "BBB")) == 2


def test_comparison_lap_data_calculates_delta():
    laps, _ = sample_team_data()
    result = comparison_lap_data(laps, "AAA", "BBB")
    assert result.iloc[0]["Delta A - B (s)"] == -2

