"""Fire drills for logging_setup: right level, right place, right shape."""

import logging

import pytest

from claim_severity.logging_setup import LOG_LEVEL_ENV_VAR, setup_logging


@pytest.fixture(autouse=True)
def restore_root_logger():
    """Save the central logbook's settings before each test and restore them after."""
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    yield
    for handler in root.handlers:
        handler.close()  # releases log files so Windows can delete them
    root.handlers = saved_handlers
    root.setLevel(saved_level)


# ── Choosing the level ────────────────────────────────────────────
def test_level_from_argument_ignores_case():
    setup_logging("debug")
    assert logging.getLogger().level == logging.DEBUG


def test_level_from_env_var_when_no_argument(monkeypatch):
    monkeypatch.setenv(LOG_LEVEL_ENV_VAR, "WARNING")
    setup_logging()
    assert logging.getLogger().level == logging.WARNING


def test_argument_beats_env_var(monkeypatch):
    monkeypatch.setenv(LOG_LEVEL_ENV_VAR, "WARNING")
    setup_logging("ERROR")
    assert logging.getLogger().level == logging.ERROR


def test_default_level_is_info(monkeypatch):
    monkeypatch.delenv(LOG_LEVEL_ENV_VAR, raising=False)
    setup_logging()
    assert logging.getLogger().level == logging.INFO


def test_unknown_level_is_rejected():
    with pytest.raises(ValueError, match="Unknown log level"):
        setup_logging("loud")


# ── Where messages go ─────────────────────────────────────────────
def test_messages_go_to_stderr_not_stdout(capsys):
    setup_logging("INFO")
    logging.getLogger("demo").info("hello")

    captured = capsys.readouterr()
    assert "| INFO     | demo | hello" in captured.err
    assert captured.out == ""


def test_log_file_and_its_folder_are_created(tmp_path):
    log_file = tmp_path / "logs" / "run.log"  # the "logs" folder doesn't exist yet
    setup_logging("INFO", log_file=log_file)
    logging.getLogger("demo").info("saved to file")

    assert "saved to file" in log_file.read_text(encoding="utf-8")


def test_calling_setup_twice_does_not_duplicate_messages(capsys):
    setup_logging("INFO")
    setup_logging("INFO")
    logging.getLogger("demo").info("only once")

    assert capsys.readouterr().err.count("only once") == 1
