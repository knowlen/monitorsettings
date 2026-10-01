"""
Base DDC/CI functionality for monitor control
"""

import re
import subprocess
import threading
import time
from typing import Dict, List, Optional, Tuple

# ddcutil flags for the per-change path. Addressing a monitor by display
# number (-d N) makes every ddcutil run re-detect all monitors first (~1 s on a
# machine with many I2C buses); --bus N skips that. --noverify drops the
# read-back after each write and --skip-ddc-checks the per-run capability
# probe. Measured on 2 x LG 4K over HDMI: -d 1.0-1.2 s, --bus + flags 0.10 s.
SET_FLAGS = ["--noverify", "--skip-ddc-checks"]
GET_FLAGS = ["--skip-ddc-checks"]


class DDCInterface:
    """
    Interface for DDC/CI communication with monitors.
    Provides low-level access to monitor settings via ddcutil.
    """

    def __init__(self) -> None:
        self.displays: List[int] = []
        self.buses: Dict[int, int] = {}  # display number -> I2C bus, from detect
        self._lock = threading.Lock()
        self._last_command_time = 0.0
        # Minimum time between synchronous DDC commands. ddcutil already
        # enforces the DDC/CI protocol delays itself, so no extra gap is needed.
        self._command_interval = 0.0

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
            # Remember each display's I2C bus so later commands can skip detection.
            self.buses = {}
            for block in re.split(r"(?m)^(?=Display \d+)", result.stdout):
                d = re.match(r"Display (\d+)", block)
                b = re.search(r"I2C bus:\s*/dev/i2c-(\d+)", block)
                if d and b:
                    self.buses[int(d.group(1))] = int(b.group(1))
            return self.displays

        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            return []

    def _target(self, display: int) -> List[str]:
        """ddcutil arguments selecting a display: its bus if known, else its number."""
        bus = self.buses.get(display)
        return ["--bus", str(bus)] if bus is not None else ["-d", str(display)]

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
                    ["ddcutil", "getvcp", vcp_code, *self._target(display), *GET_FLAGS],
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
                    ["ddcutil", "setvcp", vcp_code, str(value), *self._target(display), *SET_FLAGS],
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
            ["ddcutil", "setvcp", vcp_code, str(value), *self._target(display), *SET_FLAGS],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _wait_for_command_interval(self) -> None:
        """Ensure minimum time between DDC commands to prevent flooding"""
        current_time = time.time()
        time_since_last = current_time - self._last_command_time

        if time_since_last < self._command_interval:
            time.sleep(self._command_interval - time_since_last)

        self._last_command_time = time.time()


class AsyncDDCWorker:
    """
    Background worker that sends DDC commands asynchronously.

    At most one ddcutil process is in flight per display (they share one I2C
    bus), and when it finishes the newest pending value is sent next, so
    intermediate values are skipped and writes can never land out of order.
    """

    def __init__(self, ddc_interface: DDCInterface, update_interval: float = 0.0):
        self.ddc = ddc_interface
        # Optional extra gap between writes to the same display (seconds).
        self.update_interval = update_interval
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._pending_updates: Dict[Tuple[int, str], int] = {}
        self._last_sent: Dict[Tuple[int, str], int] = {}
        self._in_flight: Dict[int, subprocess.Popen] = {}
        self._last_send_time: Dict[int, float] = {}

    def start(self) -> None:
        """Start the background worker thread"""
        if not self.running:
            self.running = True
            self._thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._thread.start()

    def stop(self, timeout: float = 0.5) -> None:
        """Stop the background worker thread"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=timeout)

    def queue_update(self, display: int, vcp_code: str, value: int) -> None:
        """
        Queue a VCP value update to be sent asynchronously

        Args:
            display: Display number
            vcp_code: VCP code
            value: Value to set
        """
        with self._lock:
            self._pending_updates[(display, vcp_code)] = value

    def _busy(self, display: int) -> bool:
        """True while a write to this display is still running."""
        p = self._in_flight.get(display)
        if p is None:
            return False
        if p.poll() is None:
            return True
        del self._in_flight[display]
        return False

    def _worker_loop(self) -> None:
        """Send the newest pending value for each display as soon as it is free."""
        while self.running:
            time.sleep(0.01)
            now = time.time()
            to_send = []
            claimed = set()  # one write per display per pass
            with self._lock:
                for key, value in list(self._pending_updates.items()):
                    display = key[0]
                    if display in claimed or self._busy(display):
                        continue  # keep it pending; the newest value wins
                    if now - self._last_send_time.get(display, 0.0) < self.update_interval:
                        continue
                    del self._pending_updates[key]
                    if self._last_sent.get(key) == value:
                        continue
                    self._last_sent[key] = value
                    claimed.add(display)
                    to_send.append((key, value))
            for (display, vcp_code), value in to_send:
                self._in_flight[display] = self.ddc.set_vcp_value_async(display, vcp_code, value)
                self._last_send_time[display] = now
