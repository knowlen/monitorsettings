#!/usr/bin/env python3

import subprocess
import time
import threading
import sys
from typing import Dict, List, Tuple
from blessed import Terminal

class BlessedBrightnessController:
    def __init__(self):
        self.term = Terminal()
        self.displays: List[int] = []
        self.current_brightness: Dict[int, int] = {}
        self.max_brightness: Dict[int, int] = {}
        self.target_brightness: Dict[int, int] = {}
        self.last_sent_brightness: Dict[int, int] = {}
        self.selected_displays: List[int] = []
        self.increment = 5
        self.running = True
        self.update_lock = threading.Lock()
        self.last_update_time = 0
        self.update_interval = 0.5
        self.interface_lines = 0
        
    def detect_displays(self) -> bool:
        """Detect DDC/CI capable displays"""
        try:
            result = subprocess.run(
                ["ddcutil", "detect"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            import re
            displays = re.findall(r'Display (\d+)', result.stdout)
            self.displays = [int(d) for d in displays]
            
            return len(self.displays) > 0
            
        except:
            return False
    
    def get_brightness(self, display: int) -> Tuple[int, int]:
        """Get current and max brightness for a display"""
        try:
            result = subprocess.run(
                ["ddcutil", "getvcp", "0x10", "-d", str(display)],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            import re
            current_match = re.search(r'current value =\s*(\d+)', result.stdout)
            max_match = re.search(r'max value =\s*(\d+)', result.stdout)
            
            current = int(current_match.group(1)) if current_match else 50
            max_val = int(max_match.group(1)) if max_match else 100
            
            return current, max_val
            
        except:
            return 50, 100
    
    def brightness_worker(self):
        """Background thread to send DDC commands"""
        while self.running:
            time.sleep(0.1)
            
            current_time = time.time()
            if current_time - self.last_update_time < self.update_interval:
                continue
            
            updates_needed = []
            with self.update_lock:
                for display in self.displays:
                    target = self.target_brightness.get(display)
                    last_sent = self.last_sent_brightness.get(display)
                    
                    if target is not None and target != last_sent:
                        updates_needed.append((display, target))
                        self.last_sent_brightness[display] = target
            
            if updates_needed:
                self.last_update_time = current_time
                for display, value in updates_needed:
                    subprocess.Popen(
                        ["ddcutil", "setvcp", "0x10", str(value), "-d", str(display)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
    
    def draw_interface(self):
        """Draw interface using blessed terminal with maroon/port color palette"""
        # Move cursor up to overwrite previous interface
        if self.interface_lines > 0:
            print(self.term.move_up * self.interface_lines, end='')
        
        lines = []
        
        # Color palette inspired by maroon/port shirt
        # Main maroon/burgundy tones
        maroon = self.term.color_rgb(139, 69, 89)  # Closest to your shirt
        deep_wine = self.term.color_rgb(88, 44, 55)  # Darker variant
        rose_gold = self.term.color_rgb(183, 110, 121)  # Lighter accent
        
        # Complementary colors
        sage = self.term.color_rgb(87, 116, 90)  # Muted green complement
        warm_gray = self.term.color_rgb(120, 113, 108)  # Neutral
        cream = self.term.color_rgb(242, 234, 220)  # Light accent
        
        # Header with gradient effect
        lines.append(deep_wine("═" * 60))
        lines.append(maroon("       ") + rose_gold("◈") + cream(" Brightness Control ") + rose_gold("◈") + maroon("       "))
        lines.append(deep_wine("═" * 60))
        lines.append("")
        
        # Mode indicator with warm tones
        if self.selected_displays:
            mode = f"Mode: Display {', '.join(str(d) for d in self.selected_displays)}"
        else:
            mode = "Mode: ALL displays"
        lines.append(rose_gold(mode) + warm_gray(" │ ") + cream(f"Step: {self.increment}"))
        lines.append("")
        
        # Display bars with maroon theme
        for display in self.displays:
            target = self.target_brightness[display]
            max_val = self.max_brightness[display]
            percent = int(target * 100 / max_val) if max_val > 0 else 0
            
            # Selection indicator
            is_selected = not self.selected_displays or display in self.selected_displays
            indicator = rose_gold("▸") if is_selected else warm_gray("·")
            
            # Progress bar with single color
            bar_width = 40
            filled = int(target * bar_width / max_val) if max_val > 0 else 0
            
            # Simple single-color bar
            filled_bar = rose_gold("█" * filled)
            empty_bar = warm_gray("·" * (bar_width - filled))
            
            # Pending indicator
            pending = sage("◉") if target != self.last_sent_brightness.get(display, target) else " "
            
            # Compose line
            display_text = cream(f"Display {display}:")
            percent_text = rose_gold(f"{percent:3d}%")
            lines.append(f"{indicator} {display_text} [{filled_bar}{empty_bar}] {percent_text} {pending}")
        
        lines.append("")
        lines.append(warm_gray("─" * 60))
        lines.append(warm_gray("[") + cream("←/→") + warm_gray("] Brightness  [") + 
                    cream("↑/↓") + warm_gray("] Step size  [") + 
                    cream("0-9") + warm_gray("] Select  [") + 
                    cream("q/ESC") + warm_gray("] Quit"))
        
        # Print all lines, clearing to end of line for each
        for line in lines:
            print(line + self.term.clear_eol)
        
        self.interface_lines = len(lines)
    
    def adjust_brightness(self, delta: int):
        """Adjust brightness for selected displays"""
        with self.update_lock:
            displays_to_adjust = self.selected_displays if self.selected_displays else self.displays
            
            for display in displays_to_adjust:
                new_val = self.target_brightness[display] + delta
                new_val = max(0, min(new_val, self.max_brightness[display]))
                self.target_brightness[display] = new_val
    
    def run(self):
        """Main loop using blessed terminal"""
        print("Initializing brightness controller...")
        
        if not self.detect_displays():
            print(self.term.red("Error: No DDC/CI capable displays detected"))
            print("Make sure DDC/CI is enabled in your monitor's OSD menu")
            return
        
        print(f"Found {len(self.displays)} display(s)")
        print("Reading brightness levels...")
        
        # Get initial brightness
        for display in self.displays:
            current, max_val = self.get_brightness(display)
            self.current_brightness[display] = current
            self.max_brightness[display] = max_val
            self.target_brightness[display] = current
            self.last_sent_brightness[display] = current
            print(f"  Display {display}: {current}/{max_val}")
        
        print("\nStarting interactive mode...\n")
        time.sleep(1)
        
        # Start background worker
        worker = threading.Thread(target=self.brightness_worker, daemon=True)
        worker.start()
        
        # Enter cbreak mode for single key input
        with self.term.cbreak(), self.term.hidden_cursor():
            last_draw = 0
            
            while self.running:
                # Draw interface at controlled rate
                current_time = time.time()
                if current_time - last_draw >= 0.1:
                    self.draw_interface()
                    last_draw = current_time
                
                # Check for key press (non-blocking with timeout)
                key = self.term.inkey(timeout=0.05)
                
                if key:
                    if key == 'q' or key == 'Q' or key.name == 'KEY_ESCAPE':
                        break
                    elif key.name == 'KEY_RIGHT':
                        self.adjust_brightness(self.increment)
                    elif key.name == 'KEY_LEFT':
                        self.adjust_brightness(-self.increment)
                    elif key.name == 'KEY_UP':
                        self.increment = min(25, self.increment + 1)
                    elif key.name == 'KEY_DOWN':
                        self.increment = max(1, self.increment - 1)
                    elif key in ['+', '=']:
                        self.increment = min(25, self.increment + 1)
                    elif key in ['-', '_']:
                        self.increment = max(1, self.increment - 1)
                    elif key == '0':
                        self.selected_displays = []
                    elif key.isdigit() and '1' <= key <= '9':
                        display_num = int(key)
                        if display_num in self.displays:
                            self.selected_displays = [display_num]
        
        self.running = False
        worker.join(timeout=0.5)
        
        # Clear the interface area
        if self.interface_lines > 0:
            print(self.term.move_up * self.interface_lines, end='')
            for _ in range(self.interface_lines):
                print(self.term.clear_eol)
            print(self.term.move_up * self.interface_lines, end='')
        
        print("\nBrightness controller exited.")

def main():
    # Check for ddcutil
    try:
        subprocess.run(["which", "ddcutil"], capture_output=True, check=True)
    except:
        print("Error: ddcutil is not installed")
        print("Install with: sudo pacman -S ddcutil")
        print("Setup: sudo modprobe i2c-dev && sudo usermod -aG i2c $USER")
        sys.exit(1)
    
    # Check for blessed
    try:
        import blessed
    except ImportError:
        print("Error: blessed library is not installed")
        print("Install with: pip install blessed")
        sys.exit(1)
    
    controller = BlessedBrightnessController()
    try:
        controller.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()