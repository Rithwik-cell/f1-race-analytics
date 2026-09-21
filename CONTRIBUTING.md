# Contributing

## Local checks

```powershell
python -m pytest -q
python -m compileall -q src dashboard tests
python -m streamlit run dashboard/app.py
```

Keep analysis logic in `src/`, chart construction in `dashboard/charts.py`, and Streamlit layout/routing in `dashboard/app.py`.

Do not commit `data/cache/`, generated Python caches, credentials, or local Streamlit secrets. When adding a metric, document its filtering rules and add an offline test using a small sample DataFrame.

## Data-quality standard

Missing or incomplete FastF1 values should be surfaced as unavailable. Do not fabricate pit durations, telemetry, weather, or race-control events. If a future AI feature is added, every generated claim must reference processed evidence supplied through `src/ai_interfaces.py`.

