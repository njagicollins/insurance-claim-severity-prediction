"""Load and validate project settings from ``config/settings.yaml``.

Usage:
    from claim_severity.config import load_settings

    settings = load_settings()
    settings.data_generation.n_claims  # -> 50000
"""

import math
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

# This file is src/claim_severity/config.py, so parents[2] is the project root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "settings.yaml"
CONFIG_ENV_VAR = "CLAIM_SEVERITY_CONFIG"  # set this to use a different settings file


class ConfigError(ValueError):
    """The settings file is missing, unreadable, or has invalid values."""


# ── Typed settings: one small class per YAML section ──────────────
@dataclass(frozen=True)
class Paths:
    raw_data: Path
    processed_data: Path
    database: Path
    documents: Path
    models: Path
    reports: Path


@dataclass(frozen=True)
class DataGeneration:
    n_claims: int
    n_policies: int
    start_date: date
    end_date: date
    product_line_mix: dict[str, float]

@dataclass(frozen=True)
class SeverityThresholds:
    medium: float  # cost at or above this is Medium (below is Low)
    high: float    # cost at or above this is High


@dataclass(frozen=True)
class Targets:
    severity_thresholds: SeverityThresholds
    prolonged_settlement_days: int


@dataclass(frozen=True)
class Settings:
    project_name: str
    random_seed: int
    paths: Paths
    data_generation: DataGeneration
    targets: Targets


# ── Public entry point ────────────────────────────────────────────
def load_settings(config_path: str | Path | None = None) -> Settings:
    """Read, convert and validate the settings file.

    Which file is used, in order of priority:
    1. ``config_path``, if given
    2. the ``CLAIM_SEVERITY_CONFIG`` environment variable, if set
    3. ``config/settings.yaml`` in the project root
    """
    path = _resolve_config_path(config_path)
    raw = _read_yaml(path)
    try:
        settings = _build_settings(raw)
    except KeyError as err:
        raise ConfigError(f"{path}: missing setting {err}") from err
    except (TypeError, ValueError) as err:
        raise ConfigError(f"{path}: invalid setting: {err}") from err
    _validate(settings)
    return settings


# ── Private helpers (leading underscore = internal use only) ──────
def _resolve_config_path(config_path: str | Path | None) -> Path:
    chosen = config_path or os.environ.get(CONFIG_ENV_VAR) or DEFAULT_CONFIG_PATH
    path = Path(chosen)
    if not path.is_file():
        raise ConfigError(f"Settings file not found: {path}")
    return path


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as file:
            raw = yaml.safe_load(file)
    except yaml.YAMLError as err:
        raise ConfigError(f"{path}: not valid YAML: {err}") from err
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: expected sections like 'project:' at the top level")
    return raw


def _to_date(value: Any) -> date:
    # Unquoted 2020-01-01 arrives from YAML as a date already; quoted arrives as text.
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _build_settings(raw: dict[str, Any]) -> Settings:
    project = raw["project"]
    gen = raw["data_generation"]
    mix = gen["product_line_mix"]
    targets = raw["targets"]
    thresholds = targets["severity_thresholds"]
    return Settings(
        project_name=str(project["name"]),
        random_seed=int(project["random_seed"]),
        # Anchor relative paths to the project root, so the code works
        # no matter which folder you run it from.
        paths=Paths(**{key: PROJECT_ROOT / value for key, value in raw["paths"].items()}),
        data_generation=DataGeneration(
            n_claims=int(gen["n_claims"]),
            n_policies=int(gen["n_policies"]),
            start_date=_to_date(gen["start_date"]),
            end_date=_to_date(gen["end_date"]),
            product_line_mix={line: float(share) for line, share in mix.items()},
        ),
        targets=Targets(
            severity_thresholds=SeverityThresholds(
                medium=float(thresholds["medium"]),
                high=float(thresholds["high"]),
            ),
            prolonged_settlement_days=int(targets["prolonged_settlement_days"]),
        ),
    )


def _validate(settings: Settings) -> None:
    gen = settings.data_generation
    if gen.n_claims <= 0:
        raise ConfigError(f"n_claims must be positive, got {gen.n_claims}")
    if gen.n_policies <= 0:
        raise ConfigError(f"n_policies must be positive, got {gen.n_policies}")
    if gen.start_date >= gen.end_date:
        raise ConfigError(f"start_date {gen.start_date} must be before end_date {gen.end_date}")
    if any(share < 0 for share in gen.product_line_mix.values()):
        raise ConfigError("product_line_mix shares cannot be negative")
    total = sum(gen.product_line_mix.values())
    if not math.isclose(total, 1.0, abs_tol=1e-6):
        raise ConfigError(f"product_line_mix must add up to 1.0, got {total}")

    severity = settings.targets.severity_thresholds
    if not 0 < severity.medium < severity.high:
        raise ConfigError(
            "severity_thresholds must satisfy 0 < medium < high, "
            f"got medium={severity.medium}, high={severity.high}"
        )
    if settings.targets.prolonged_settlement_days <= 0:
        raise ConfigError(
            "prolonged_settlement_days must be positive, "
            f"got {settings.targets.prolonged_settlement_days}"
        )
