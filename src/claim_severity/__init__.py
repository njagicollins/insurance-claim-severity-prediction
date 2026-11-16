"""Claim severity and prolonged-settlement prediction for commercial insurance."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("claim-severity")
except PackageNotFoundError:  # code is running without being installed
    __version__ = "0.0.0"
