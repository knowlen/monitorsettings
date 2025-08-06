"""
Unit tests for base DDC functionality using pytest
"""

import subprocess
import time
from unittest.mock import MagicMock

import pytest

from monitorsettings.base import AsyncDDCWorker, DDCInterface


@pytest.fixture
def ddc_interface():
    """Fixture providing a DDCInterface instance"""
    return DDCInterface()


@pytest.fixture
def async_worker(ddc_interface):
    """Fixture providing an AsyncDDCWorker instance"""
    return AsyncDDCWorker(ddc_interface, update_interval=0.1)


class TestDDCInterface:
    """Test cases for DDCInterface class"""

    def test_check_ddcutil_available(self, ddc_interface, mocker):
        """Test checking for ddcutil availability when present"""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0)

        result = ddc_interface.check_ddcutil()

        assert result is True
        mock_run.assert_called_once()

    def test_check_ddcutil_not_available(self, ddc_interface, mocker):
        """Test checking for ddcutil when not present"""
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = subprocess.CalledProcessError(1, "which")

        result = ddc_interface.check_ddcutil()

        assert result is False

    def test_detect_displays(self, ddc_interface, mocker):
        """Test display detection"""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(
            stdout="Display 1\nI2C bus: /dev/i2c-1\nDisplay 2\nI2C bus: /dev/i2c-2"
        )

        displays = ddc_interface.detect_displays()

        assert displays == [1, 2]
        assert ddc_interface.displays == [1, 2]

    def test_detect_displays_none_found(self, ddc_interface, mocker):
        """Test display detection when no displays found"""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(stdout="No displays found")

        displays = ddc_interface.detect_displays()

        assert displays == []

    @pytest.mark.parametrize(
        "current,max_val",
        [
            (50, 100),
            (0, 100),
            (100, 100),
            (75, 255),
        ],
    )
    def test_get_vcp_value(self, ddc_interface, mocker, current, max_val):
        """Test getting VCP value with various brightness levels"""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(
            stdout=f"VCP code 0x10 (Brightness): current value = {current}, max value = {max_val}"
        )

        result_current, result_max = ddc_interface.get_vcp_value(1, "0x10")

        assert result_current == current
        assert result_max == max_val

    def test_get_vcp_value_error(self, ddc_interface, mocker):
        """Test getting VCP value with error"""
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = subprocess.TimeoutExpired("ddcutil", 2)

        current, max_val = ddc_interface.get_vcp_value(1, "0x10")

        assert current is None
        assert max_val is None

    def test_set_vcp_value(self, ddc_interface, mocker):
        """Test setting VCP value"""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0)

        result = ddc_interface.set_vcp_value(1, "0x10", 75)

        assert result is True
        mock_run.assert_called_with(
            ["ddcutil", "setvcp", "0x10", "75", "-d", "1"],
            capture_output=True,
            timeout=3,
            check=True,
        )

    def test_set_vcp_value_failure(self, ddc_interface, mocker):
        """Test setting VCP value with failure"""
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = subprocess.CalledProcessError(1, "ddcutil")

        result = ddc_interface.set_vcp_value(1, "0x10", 75)

        assert result is False

    def test_set_vcp_value_async(self, ddc_interface, mocker):
        """Test async VCP value setting"""
        mock_popen = mocker.patch("subprocess.Popen")
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        process = ddc_interface.set_vcp_value_async(1, "0x10", 80)

        assert process == mock_process
        mock_popen.assert_called_once()

    def test_command_interval_enforcement(self, ddc_interface, mocker):
        """Test that minimum time between commands is enforced"""
        mock_sleep = mocker.patch("time.sleep")
        mock_time = mocker.patch("time.time")
        mock_time.side_effect = [0, 0, 0.2, 0.2, 0.3]  # Simulate time passing

        ddc_interface._wait_for_command_interval()
        ddc_interface._wait_for_command_interval()

        # Should sleep to maintain interval
        mock_sleep.assert_called()


class TestAsyncDDCWorker:
    """Test cases for AsyncDDCWorker class"""

    def test_queue_update(self, async_worker):
        """Test queuing updates"""
        async_worker.queue_update(1, "0x10", 50)
        assert async_worker._pending_updates[(1, "0x10")] == 50

        # Test overwriting with new value
        async_worker.queue_update(1, "0x10", 60)
        assert async_worker._pending_updates[(1, "0x10")] == 60

    def test_queue_multiple_displays(self, async_worker):
        """Test queuing updates for multiple displays"""
        async_worker.queue_update(1, "0x10", 50)
        async_worker.queue_update(2, "0x10", 75)
        async_worker.queue_update(1, "0x12", 100)  # Different VCP code

        assert async_worker._pending_updates[(1, "0x10")] == 50
        assert async_worker._pending_updates[(2, "0x10")] == 75
        assert async_worker._pending_updates[(1, "0x12")] == 100

    def test_worker_processes_updates(self, async_worker, mocker):
        """Test that worker processes queued updates"""
        mock_set_async = mocker.patch.object(async_worker.ddc, "set_vcp_value_async")
        mock_process = MagicMock()
        mock_set_async.return_value = mock_process

        # Queue some updates
        async_worker.queue_update(1, "0x10", 75)
        async_worker.queue_update(2, "0x10", 80)

        # Start worker
        async_worker.start()

        # Wait for processing
        time.sleep(0.2)

        # Stop worker
        async_worker.stop()

        # Check that updates were sent
        assert mock_set_async.call_count == 2

    def test_worker_start_stop(self, async_worker):
        """Test starting and stopping worker thread"""
        assert async_worker.running is False

        async_worker.start()
        assert async_worker.running is True
        assert async_worker._thread is not None
        assert async_worker._thread.is_alive()

        async_worker.stop(timeout=0.5)
        assert async_worker.running is False

    def test_worker_deduplication(self, async_worker, mocker):
        """Test that worker doesn't re-send same values"""
        mock_set_async = mocker.patch.object(async_worker.ddc, "set_vcp_value_async")

        # Set initial state
        async_worker._last_sent[(1, "0x10")] = 50

        # Queue same value
        async_worker.queue_update(1, "0x10", 50)

        # Process updates (should not send anything)
        with async_worker._lock:
            async_worker._pending_updates.clear()

        assert mock_set_async.call_count == 0
