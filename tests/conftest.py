"""Pytest configuration and shared fixtures."""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (no external dependencies)")
    config.addinivalue_line(
        "markers", "integration: Integration tests (require IBKR connection)"
    )
    config.addinivalue_line("markers", "slow: Slow running tests")

