import pandas as pd

from src.data_processing import format_timedelta


def test_format_timedelta():
    assert format_timedelta(pd.Timedelta(seconds=91.234)) == "1:31.234"
    assert format_timedelta(pd.NaT) == "—"
