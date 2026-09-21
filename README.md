# F1 Race Analytics Hub

Portfolio-quality Formula 1 race analysis built with Python, FastF1, Pandas, Plotly, and Streamlit. The application turns a selected F1 session into an interactive engineering analysis workspace while keeping raw-data limitations visible.

## Why this project exists

F1 timing data is a realistic engineering dataset: large, time-based, incomplete in places, and rich enough to connect vehicle performance with strategy and race context. This project demonstrates data loading, quality-aware processing, statistical summaries, interactive visualization, caching, testing, and modular application design.

## Features

- Dynamic season, event, and session selection through FastF1's event schedule.
- Race overview with finishing order, winner, circuit, date, lap count, fastest lap, and position progression.
- Driver analysis and two-driver comparison with lap, sector, speed, position, and delta views.
- Team analysis with team summaries, points, fastest laps, top speed, and teammate comparison.
- Lap and sector analysis with valid/inaccurate/deleted records kept visible.
- Tyre strategy, stint statistics, tyre-life trends, and pit-stop marker timelines.
- Telemetry for speed, throttle, brake, RPM, gear, and distance.
- Distance-aligned telemetry comparison for two drivers.
- Weather trends and observed weather ranges.
- Race-control messages, flags, track status, and a unified race timeline.
- Data-quality reporting for missing, deleted, inaccurate, and incomplete records.

## Architecture

```text
dashboard/app.py          Streamlit UI and view routing
dashboard/charts.py       Plotly chart builders
src/fastf1_loader.py      FastF1 cache and session loading
src/data_processing.py    Reusable lap cleaning and validity rules
src/driver_analysis.py    Driver summaries and driver-level data
src/team_analysis.py      Team and driver-comparison metrics
src/lap_analysis.py       Lap statistics, sectors, and quality counts
src/tyre_analysis.py      Stints, tyre-life trends, and pit markers
src/telemetry_analysis.py Telemetry extraction and distance alignment
src/weather_analysis.py   Weather normalization and summaries
src/race_events.py       Event cleaning and unified timeline
tests/                    Offline unit tests using sample DataFrames
data/cache/               Local FastF1 cache, ignored by Git
```

The UI is deliberately separated from analysis logic. This makes the calculations testable without starting Streamlit and leaves clear extension points for future AI features.

## AI extension point

`src/ai_interfaces.py` defines an evidence-grounded interface for future AI race summaries, driver coaching, knowledge search, or prediction work. It does not call a model. `AnalysisContext` accepts only processed observations, while `AnalysisResult` records evidence sources and limitations. This prevents an AI layer from presenting unsupported claims as if they came from FastF1.

## Installation

Use Python 3.13 or a compatible Python version:

```powershell
cd "C:\Users\Admin\Documents\New project"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run the application

```powershell
python -m streamlit run dashboard/app.py
```

Or run `run_app.bat`.

The application starts with an empty race-selection landing screen; it does not load a Grand Prix automatically. The 2026 Italian Grand Prix Race remains a real development test case that can be explicitly selected. The first session load downloads available FastF1 data; later loads reuse `data/cache/`.

## Test

```powershell
python -m pytest -q
python -m compileall -q src dashboard tests
```

The tests do not require internet access. They use small sample DataFrames to verify filtering, fastest laps, sectors, stints, pit markers, telemetry alignment, weather, events, team summaries, and comparison deltas.

GitHub Actions runs the same tests and Python compilation checks for pushes and pull requests. See [CONTRIBUTING.md](CONTRIBUTING.md) for the local development workflow.

## FastF1 caching

`src/fastf1_loader.py` enables a project-local FastF1 cache at `data/cache/`. Streamlit caches the loaded session as a resource and caches selected telemetry as data. The cache is excluded from Git because it can be large and machine-specific.

FastF1 warnings are not automatically treated as fatal. The dashboard reports missing or inaccurate records and avoids inventing values when a feed is incomplete.

## Data interpretation rules

- Valid-lap calculations require a lap time, `IsAccurate` not false, and `Deleted` not true.
- Raw records remain available for data-quality inspection.
- Theoretical best lap means best observed S1 + S2 + S3, potentially from different laps.
- Tyre-life regression is an observed association, not a causal degradation model.
- Pit-stop duration is omitted unless the timing feed provides a reliable measurement.
- Telemetry comparison is aligned by distance because sample timestamps and counts can differ.
- Weather, race-control, and track-status values are shown only when supplied by FastF1.

## Streamlit Community Cloud deployment

1. Push this repository to GitHub.
2. Create a Streamlit Community Cloud app pointing to `dashboard/app.py`.
3. Keep `requirements.txt` at repository root.
4. Do not commit `data/cache/`, credentials, or `.streamlit/secrets.toml`.
5. Allow additional time for the first FastF1 session download.

The app contains no machine-specific absolute paths in runtime code.

## Known limitations

FastF1 coverage varies by season, session, and data channel. Some historical sessions have incomplete telemetry, weather, or race-control data. The application handles those cases with warnings and empty-state messages. The 2026 development session is real data, but future sessions can change as upstream data becomes available.

## Future extensions

The modular data layer supports future, evidence-based features such as an AI race summarizer, driver coach, F1 knowledge assistant, and outcome prediction. These should consume processed FastF1-derived data and explicitly cite the underlying observations; no fake AI analysis is included here.
