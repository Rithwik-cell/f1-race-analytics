"""Application configuration and project paths."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

DEFAULT_SEASON = 2026
TEST_EVENT = "Italian Grand Prix"
TEST_SESSION = "R"

SUPPORTED_SESSIONS = {
    "FP1": "Practice 1",
    "FP2": "Practice 2",
    "FP3": "Practice 3",
    "Q": "Qualifying",
    "SQ": "Sprint Qualifying",
    "Sprint": "Sprint",
    "R": "Race",
}


def ensure_project_directories() -> None:
    """Create runtime directories without requiring machine-specific paths."""
    for directory in (CACHE_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR):
        directory.mkdir(parents=True, exist_ok=True)
