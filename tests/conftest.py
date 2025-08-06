"""
Shared pytest fixtures and configuration
"""

import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_subprocess(mocker):
    """Mock subprocess module for DDC commands"""
    mock_run = mocker.patch("subprocess.run")
    mock_popen = mocker.patch("subprocess.Popen")
    return {"run": mock_run, "popen": mock_popen}


@pytest.fixture
def mock_ddcutil_available(mock_subprocess):
    """Mock ddcutil as available on system"""
    mock_subprocess["run"].return_value = MagicMock(returncode=0)
    return mock_subprocess


@pytest.fixture
def mock_displays_detected(mock_subprocess):
    """Mock successful display detection"""

    def run_side_effect(*args, **kwargs):
        if "which" in args[0]:
            return MagicMock(returncode=0)
        elif "detect" in args[0]:
            return MagicMock(
                stdout="Display 1\nI2C bus: /dev/i2c-1\nDisplay 2\nI2C bus: /dev/i2c-2"
            )
        elif "getvcp" in args[0]:
            return MagicMock(
                stdout="VCP code 0x10 (Brightness): current value = 50, max value = 100"
            )
        return MagicMock(returncode=0)

    mock_subprocess["run"].side_effect = run_side_effect
    return mock_subprocess


@pytest.fixture
def mock_no_displays(mock_subprocess):
    """Mock no displays detected"""

    def run_side_effect(*args, **kwargs):
        if "which" in args[0]:
            return MagicMock(returncode=0)
        elif "detect" in args[0]:
            return MagicMock(stdout="No displays found")
        return MagicMock(returncode=1)

    mock_subprocess["run"].side_effect = run_side_effect
    return mock_subprocess


@pytest.fixture(autouse=True)
def reset_imports():
    """Reset import state between tests"""
    # Store original modules
    original_modules = sys.modules.copy()

    yield

    # Restore original modules
    sys.modules = original_modules


@pytest.fixture
def mock_time(mocker):
    """Mock time functions for testing delays"""
    mock_time = mocker.patch("time.time")
    mock_sleep = mocker.patch("time.sleep")
    return {"time": mock_time, "sleep": mock_sleep}


@pytest.fixture
def sample_display_config():
    """Sample display configuration for testing"""
    return {
        "displays": [1, 2],
        "current_brightness": {1: 50, 2: 75},
        "max_brightness": {1: 100, 2: 100},
        "target_brightness": {1: 50, 2: 75},
    }
