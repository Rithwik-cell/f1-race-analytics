import pandas as pd

from src.telemetry_analysis import prepare_telemetry, resample_by_distance, telemetry_summary


def sample_telemetry():
    return pd.DataFrame(
        {
            "Distance": [0.0, 50.0, 100.0],
            "Speed": [100.0, 150.0, 120.0],
            "Throttle": [50.0, 100.0, 20.0],
            "Brake": [0, 0, 1],
            "RPM": [8000, 10000, 9000],
            "nGear": [3, 5, 4],
            "Ignored": [1, 2, 3],
        }
    )


def test_prepare_telemetry_keeps_channels_and_distance():
    result = prepare_telemetry(sample_telemetry())
    assert "Ignored" not in result
    assert list(result["Distance"]) == [0.0, 50.0, 100.0]


def test_resample_by_distance_creates_common_grid():
    result = resample_by_distance(sample_telemetry(), samples=5)
    assert len(result) == 5
    assert result.iloc[0]["Distance"] == 0
    assert result.iloc[-1]["Distance"] == 100


def test_telemetry_summary_reports_samples_and_distance():
    result = telemetry_summary(sample_telemetry())
    assert result["Samples"] == 3
    assert result["Distance"] == "100 m"

