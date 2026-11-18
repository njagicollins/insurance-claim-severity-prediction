"""Tests for claim_severity.config: does the receptionist accept good forms and reject bad ones?"""

import dataclasses
from datetime import date
from pathlib import Path

import pytest
import yaml

from claim_severity.config import (
    CONFIG_ENV_VAR,
    DEFAULT_CONFIG_PATH,
    PROJECT_ROOT,
    ConfigError,
    Settings,
    load_settings,
)


# ── Helpers ───────────────────────────────────────────────────────
@pytest.fixture
def valid_raw() -> dict:
    """A fresh copy of the real settings as a plain dictionary, for one test to edit."""
    with DEFAULT_CONFIG_PATH.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def write_yaml(folder: Path, data: dict) -> Path:
    """Save a settings dictionary as a YAML file and return its path."""
    path = folder / "settings.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


# ── Happy path: good settings load correctly ──────────────────────
def test_default_settings_load():
    settings = load_settings()
    assert isinstance(settings, Settings)
    assert settings.data_generation.n_claims > 0
    assert settings.data_generation.start_date < settings.data_generation.end_date


def test_paths_are_anchored_to_project_root():
    database = load_settings().paths.database
    assert database.is_absolute()
    assert database.is_relative_to(PROJECT_ROOT)


def test_settings_are_read_only():
    settings = load_settings()
    with pytest.raises(dataclasses.FrozenInstanceError):
        settings.random_seed = 7


def test_unquoted_dates_are_accepted(tmp_path, valid_raw):
    valid_raw["data_generation"]["start_date"] = date(2021, 6, 1)  # saved without quotes
    settings = load_settings(write_yaml(tmp_path, valid_raw))
    assert settings.data_generation.start_date == date(2021, 6, 1)


def test_env_var_chooses_the_settings_file(tmp_path, valid_raw, monkeypatch):
    valid_raw["data_generation"]["n_claims"] = 1000
    monkeypatch.setenv(CONFIG_ENV_VAR, str(write_yaml(tmp_path, valid_raw)))
    assert load_settings().data_generation.n_claims == 1000


# ── Sad path: bad settings are rejected with a clear message ──────
@pytest.mark.parametrize(
    ("section", "key", "bad_value", "expected_message"),
    [
        ("data_generation", "n_claims", 0, "n_claims must be positive"),
        ("data_generation", "n_claims", "lots", "invalid setting"),
        ("data_generation", "start_date", "2030-01-01", "must be before end_date"),
        ("data_generation", "end_date", "31/12/2025", "invalid setting"),
        ("project", "random_seed", "abc", "invalid setting"),
        ("paths", "databse", "data/typo.db", "invalid setting"),  # misspelled key
    ],
)
def test_bad_values_are_rejected(tmp_path, valid_raw, section, key, bad_value, expected_message):
    valid_raw[section][key] = bad_value
    with pytest.raises(ConfigError, match=expected_message):
        load_settings(write_yaml(tmp_path, valid_raw))


def test_mix_must_add_up_to_one(tmp_path, valid_raw):
    valid_raw["data_generation"]["product_line_mix"]["commercial_property"] = 0.30
    with pytest.raises(ConfigError, match="must add up to 1.0"):
        load_settings(write_yaml(tmp_path, valid_raw))


def test_mix_cannot_be_negative(tmp_path, valid_raw):
    valid_raw["data_generation"]["product_line_mix"]["commercial_auto"] = -0.35
    with pytest.raises(ConfigError, match="cannot be negative"):
        load_settings(write_yaml(tmp_path, valid_raw))


def test_missing_setting_is_named(tmp_path, valid_raw):
    del valid_raw["data_generation"]["n_claims"]
    with pytest.raises(ConfigError, match="missing setting 'n_claims'"):
        load_settings(write_yaml(tmp_path, valid_raw))


def test_missing_file_is_reported(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_settings(tmp_path / "does_not_exist.yaml")


@pytest.mark.parametrize(
    ("file_text", "expected_message"),
    [
        ("project: [never closed", "not valid YAML"),
        ("", "expected sections"),
    ],
)
def test_broken_or_empty_file_is_rejected(tmp_path, file_text, expected_message):
    path = tmp_path / "settings.yaml"
    path.write_text(file_text, encoding="utf-8")
    with pytest.raises(ConfigError, match=expected_message):
        load_settings(path)
