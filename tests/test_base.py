"""
Tests for base DDC functionality
"""

import unittest
from unittest.mock import patch, MagicMock, call
import subprocess
from monitorsettings.base import DDCInterface, AsyncDDCWorker


class TestDDCInterface(unittest.TestCase):
    """Test cases for DDCInterface class"""
    
    def setUp(self):
        self.ddc = DDCInterface()
    
    @patch('subprocess.run')
    def test_check_ddcutil_available(self, mock_run):
        """Test checking for ddcutil availability when present"""
        mock_run.return_value = MagicMock(returncode=0)
        result = self.ddc.check_ddcutil()
        self.assertTrue(result)
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_check_ddcutil_not_available(self, mock_run):
        """Test checking for ddcutil when not present"""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'which')
        result = self.ddc.check_ddcutil()
        self.assertFalse(result)
    
    @patch('subprocess.run')
    def test_detect_displays(self, mock_run):
        """Test display detection"""
        mock_run.return_value = MagicMock(
            stdout="Display 1\nI2C bus: /dev/i2c-1\nDisplay 2\nI2C bus: /dev/i2c-2"
        )
        displays = self.ddc.detect_displays()
        self.assertEqual(displays, [1, 2])
        self.assertEqual(self.ddc.displays, [1, 2])
    
    @patch('subprocess.run')
    def test_detect_displays_none_found(self, mock_run):
        """Test display detection when no displays found"""
        mock_run.return_value = MagicMock(stdout="No displays found")
        displays = self.ddc.detect_displays()
        self.assertEqual(displays, [])
    
    @patch('subprocess.run')
    def test_get_vcp_value(self, mock_run):
        """Test getting VCP value"""
        mock_run.return_value = MagicMock(
            stdout="VCP code 0x10 (Brightness): current value = 50, max value = 100"
        )
        current, max_val = self.ddc.get_vcp_value(1, "0x10")
        self.assertEqual(current, 50)
        self.assertEqual(max_val, 100)
    
    @patch('subprocess.run')
    def test_get_vcp_value_error(self, mock_run):
        """Test getting VCP value with error"""
        mock_run.side_effect = subprocess.TimeoutExpired('ddcutil', 2)
        current, max_val = self.ddc.get_vcp_value(1, "0x10")
        self.assertIsNone(current)
        self.assertIsNone(max_val)
    
    @patch('subprocess.run')
    def test_set_vcp_value(self, mock_run):
        """Test setting VCP value"""
        mock_run.return_value = MagicMock(returncode=0)
        result = self.ddc.set_vcp_value(1, "0x10", 75)
        self.assertTrue(result)
        mock_run.assert_called_with(
            ["ddcutil", "setvcp", "0x10", "75", "-d", "1"],
            capture_output=True,
            timeout=3,
            check=True
        )
    
    @patch('subprocess.Popen')
    def test_set_vcp_value_async(self, mock_popen):
        """Test async VCP value setting"""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        
        process = self.ddc.set_vcp_value_async(1, "0x10", 80)
        self.assertEqual(process, mock_process)
        mock_popen.assert_called_once()


class TestAsyncDDCWorker(unittest.TestCase):
    """Test cases for AsyncDDCWorker class"""
    
    def setUp(self):
        self.ddc = DDCInterface()
        self.worker = AsyncDDCWorker(self.ddc, update_interval=0.1)
    
    def test_queue_update(self):
        """Test queuing updates"""
        self.worker.queue_update(1, "0x10", 50)
        self.assertEqual(self.worker._pending_updates[(1, "0x10")], 50)
        
        self.worker.queue_update(1, "0x10", 60)
        self.assertEqual(self.worker._pending_updates[(1, "0x10")], 60)
    
    @patch.object(DDCInterface, 'set_vcp_value_async')
    def test_worker_processes_updates(self, mock_set_async):
        """Test that worker processes queued updates"""
        mock_process = MagicMock()
        mock_set_async.return_value = mock_process
        
        # Queue some updates
        self.worker.queue_update(1, "0x10", 75)
        self.worker.queue_update(2, "0x10", 80)
        
        # Start worker
        self.worker.start()
        
        # Wait for processing
        import time
        time.sleep(0.2)
        
        # Stop worker
        self.worker.stop()
        
        # Check that updates were sent
        self.assertEqual(mock_set_async.call_count, 2)


if __name__ == '__main__':
    unittest.main()