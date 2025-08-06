"""
Base class for backlight/brightness controllers
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from ...base import DDCInterface, AsyncDDCWorker


class BacklightController(ABC):
    """
    Abstract base class for backlight/brightness controllers.
    Handles DDC communication and state management.
    """
    
    # VCP code for brightness control
    BRIGHTNESS_VCP_CODE = "0x10"
    
    def __init__(self):
        self.ddc = DDCInterface()
        self.worker = AsyncDDCWorker(self.ddc)
        
        # Display state
        self.displays: List[int] = []
        self.current_brightness: Dict[int, int] = {}
        self.max_brightness: Dict[int, int] = {}
        self.target_brightness: Dict[int, int] = {}
        self.selected_displays: List[int] = []  # Empty means all displays
        
        # Control settings
        self.increment = 5
        self.running = True
        
    def initialize(self) -> bool:
        """
        Initialize DDC interface and detect displays
        
        Returns:
            True if successful, False otherwise
        """
        if not self.ddc.check_ddcutil():
            return False
            
        self.displays = self.ddc.detect_displays()
        if not self.displays:
            return False
            
        # Get initial brightness for all displays
        for display in self.displays:
            current, max_val = self.get_brightness(display)
            if current is not None and max_val is not None:
                self.current_brightness[display] = current
                self.max_brightness[display] = max_val
                self.target_brightness[display] = current
            else:
                # Use defaults if can't read
                self.current_brightness[display] = 50
                self.max_brightness[display] = 100
                self.target_brightness[display] = 50
                
        return True
    
    def get_brightness(self, display: int) -> tuple[Optional[int], Optional[int]]:
        """
        Get current and max brightness for a display
        
        Args:
            display: Display number
            
        Returns:
            Tuple of (current, max) or (None, None) on error
        """
        return self.ddc.get_vcp_value(display, self.BRIGHTNESS_VCP_CODE)
    
    def set_brightness(self, display: int, value: int):
        """
        Set brightness for a display (queued for async sending)
        
        Args:
            display: Display number
            value: Brightness value
        """
        self.worker.queue_update(display, self.BRIGHTNESS_VCP_CODE, value)
    
    def adjust_brightness(self, delta: int):
        """
        Adjust brightness for selected displays
        
        Args:
            delta: Amount to adjust (positive or negative)
        """
        displays_to_adjust = self.selected_displays if self.selected_displays else self.displays
        
        for display in displays_to_adjust:
            new_val = self.target_brightness[display] + delta
            new_val = max(0, min(new_val, self.max_brightness[display]))
            self.target_brightness[display] = new_val
            self.set_brightness(display, new_val)
    
    def select_display(self, display_num: Optional[int] = None):
        """
        Select which display(s) to control
        
        Args:
            display_num: Display number to select, or None for all displays
        """
        if display_num is None:
            self.selected_displays = []
        elif display_num in self.displays:
            self.selected_displays = [display_num]
    
    def start_worker(self):
        """Start the async DDC worker thread"""
        self.worker.start()
    
    def stop_worker(self):
        """Stop the async DDC worker thread"""
        self.worker.stop()
    
    @abstractmethod
    def run(self):
        """Main run loop - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def cleanup(self):
        """Cleanup on exit - must be implemented by subclasses"""
        pass