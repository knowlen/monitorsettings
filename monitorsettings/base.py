"""
Base DDC/CI functionality for monitor control
"""

import re
import subprocess
import threading
import time
from typing import Dict, List, Optional, Tuple


class DDCInterface:
    """
    Interface for DDC/CI communication with monitors.
    Provides low-level access to monitor settings via ddcutil.
    """

    def __init__(self):
        self.displays: List[int] = []
        self._lock = threading.Lock()
        self._last_command_time = 0
        self._command_interval = 0.5  # Minimum time between DDC commands

    def check_ddcutil(self) -> bool:
        """Check if ddcutil is available on the system"""
        try:
            subprocess.run(["which", "ddcutil"], capture_output=True, check=True, timeout=2)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def detect_displays(self) -> List[int]:
        """
        Detect DDC/CI capable displays

        Returns:
            List of display numbers
        """
        try:
            result = subprocess.run(
                ["ddcutil", "detect"], capture_output=True, text=True, timeout=5
            )

            displays = re.findall(r"Display (\d+)", result.stdout)
            self.displays = [int(d) for d in displays]
            return self.displays

        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            return []

    def get_vcp_value(self, display: int, vcp_code: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Get a VCP (Virtual Control Panel) value from a display

        Args:
            display: Display number
            vcp_code: VCP code (e.g., "0x10" for brightness)

        Returns:
            Tuple of (current_value, max_value) or (None, None) on error
        """
        try:
            with self._lock:
                self._wait_for_command_interval()

                result = subprocess.run(
                    ["ddcutil", "getvcp", vcp_code, "-d", str(display)],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )

                current_match = re.search(r"current value =\s*(\d+)", result.stdout)
                max_match = re.search(r"max value =\s*(\d+)", result.stdout)

                if current_match and max_match:
                    return int(current_match.group(1)), int(max_match.group(1))

        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass

        return None, None

    def set_vcp_value(self, display: int, vcp_code: str, value: int) -> bool:
        """
        Set a VCP value on a display

        Args:
            display: Display number
            vcp_code: VCP code (e.g., "0x10" for brightness)
            value: Value to set

        Returns:
            True if successful, False otherwise
        """
        try:
            with self._lock:
                self._wait_for_command_interval()

                subprocess.run(
                    ["ddcutil", "setvcp", vcp_code, str(value), "-d", str(display)],
                    capture_output=True,
                    timeout=3,
                    check=True,
                )
                return True

        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            return False

    def set_vcp_value_async(self, display: int, vcp_code: str, value: int) -> subprocess.Popen:
        """
        Set a VCP value asynchronously (fire and forget)

        Args:
            display: Display number
            vcp_code: VCP code
            value: Value to set

        Returns:
            Popen process object
        """
        return subprocess.Popen(
            ["ddcutil", "setvcp", vcp_code, str(value), "-d", str(display)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _wait_for_command_interval(self):
        """Ensure minimum time between DDC commands to prevent flooding"""
        current_time = time.time()
        time_since_last = current_time - self._last_command_time

        if time_since_last < self._command_interval:
            time.sleep(self._command_interval - time_since_last)

        self._last_command_time = time.time()


class AsyncDDCWorker:
    """
    Background worker for sending DDC commands asynchronously with debouncing
    """

    def __init__(self, ddc_interface: DDCInterface, update_interval: float = 0.5):
        self.ddc = ddc_interface
        self.update_interval = update_interval
        self.running = False
        self._thread = None
        self._lock = threading.Lock()
        self._pending_updates: Dict[Tuple[int, str], int] = {}
        self._last_sent: Dict[Tuple[int, str], int] = {}
        self._last_update_time = 0

    def start(self):
        """Start the background worker thread"""
        if not self.running:
            self.running = True
            self._thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._thread.start()

    def stop(self, timeout: float = 0.5):
        """Stop the background worker thread"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=timeout)

    def queue_update(self, display: int, vcp_code: str, value: int):
        """
        Queue a VCP value update to be sent asynchronously

        Args:
            display: Display number
            vcp_code: VCP code
            value: Value to set
        """
        with self._lock:
            self._pending_updates[(display, vcp_code)] = value

    def _worker_loop(self):
        """Main worker loop for processing queued updates"""
        while self.running:
            time.sleep(0.05)  # Check every 50ms

            current_time = time.time()
            if current_time - self._last_update_time < self.update_interval:
                continue

            updates_to_send = []

            with self._lock:
                for key, value in self._pending_updates.items():
                    if self._last_sent.get(key) != value:
                        updates_to_send.append((key, value))
                        self._last_sent[key] = value

                self._pending_updates.clear()

            if updates_to_send:
                self._last_update_time = current_time
                processes = []

                for (display, vcp_code), value in updates_to_send:
                    p = self.ddc.set_vcp_value_async(display, vcp_code, value)
                    processes.append(p)

                # Don't wait for completion - fire and forget
                for p in processes:
                    try:
                        p.wait(timeout=0.01)
                    except subprocess.TimeoutExpired:
                        pass
