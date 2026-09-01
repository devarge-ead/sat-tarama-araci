"""Load and save user preferences in a JSON file beside the executable."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

SETTINGS_FILENAME = "sat_tarama_settings.json"


def get_data_dir() -> Path:
    """Return the directory where the settings file is stored.

    When frozen with PyInstaller the JSON lives next to the exe; during
    development it lives in the project root.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    override = os.environ.get("SAT_TARAMA_DATA_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent.parent


def settings_path() -> Path:
    """The absolute path of the settings JSON file."""
    return get_data_dir() / SETTINGS_FILENAME


@dataclass
class YearConfig:
    """Serializable representation of an added year folder."""

    path: str
    checked: bool = True
    unchecked_months: list[int] = field(default_factory=list)


@dataclass
class Settings:
    """All user preferences persisted between sessions."""

    years: list[YearConfig] = field(default_factory=list)
    last_search: dict[str, str] = field(default_factory=dict)
    window_geometry: dict[str, int] = field(default_factory=dict)
    window_state: list[int] = field(default_factory=list)


def load() -> Settings:
    """Load settings from disk, returning defaults when absent or invalid."""
    path = settings_path()
    data: dict = {}
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        data = {}

    settings = Settings()
    for raw in data.get("years", []):
        try:
            settings.years.append(YearConfig(
                path=str(raw["path"]),
                checked=bool(raw.get("checked", True)),
                unchecked_months=[int(m) for m in raw.get("unchecked_months", [])],
            ))
        except (KeyError, TypeError, ValueError):
            continue
    settings.last_search = {k: str(v) for k, v in data.get("last_search", {}).items()}
    settings.window_geometry = {k: int(v) for k, v in
                                data.get("window_geometry", {}).items()}
    settings.window_state = [int(v) for v in data.get("window_state", [])]
    return settings


def save(settings: Settings) -> None:
    """Persist settings to disk, creating the folder if required."""
    data = asdict(settings)
    path = settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
    except OSError:
        # Failing to persist settings must never crash the application.
        return