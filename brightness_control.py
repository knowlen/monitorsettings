#!/usr/bin/env python3

import curses
import subprocess
import time
import threading
import sys
from typing import Dict, List, Tuple
import os

class BrightnessController:
    def __init__(self):
        self.displays: List[int] = []
        self.current_brightness: Dict[int, int] = {}
        self.max_brightness: Dict[int, int] = {}
        self.target_brightness: Dict[int, int] = {}
        self.last_sent_brightness: Dict[int, int] = {}
        self.selected_displays: List[int] = []  # Empty means all displays
        self.increment = 5
        self.running = True
        self.update_lock = threading.Lock()
        self.last_update_time = 0
        self.update_interval = 3 #0.1  # Only send DDC commands every 100ms
        
    def detect_displays(self) -> bool:
        """Detect DDC/CI capable displays"""
        try:
            result = subprocess.run(
                ["ddcutil", "detect"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            # Extract display numbers
            import re
            displays = re.findall(r'Display (\d+)', result.stdout)
            self.displays = [int(d) for d in displays]
            
            return len(self.displays) > 0
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
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
        """Background thread to send DDC commands with debouncing"""
        while self.running:
            time.sleep(0.05)  # Check every 50ms
            
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
                # Send all updates in parallel
                processes = []
                for display, value in updates_needed:
                    p = subprocess.Popen(
                        ["ddcutil", "setvcp", "0x10", str(value), "-d", str(display)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    processes.append(p)
                
                # Don't wait for completion - fire and forget
                for p in processes:
                    try:
                        p.wait(timeout=0.01)  # Very short wait
                    except subprocess.TimeoutExpired:
                        pass  # Let it run in background
    
    def init_displays(self, stdscr):
        """Initialize display detection and brightness reading"""
        stdscr.clear()
        stdscr.addstr(0, 0, "Detecting displays...")
        stdscr.refresh()
        
        if not self.detect_displays():
            stdscr.addstr(2, 0, "Error: No DDC/CI capable displays detected")
            stdscr.addstr(3, 0, "Make sure DDC/CI is enabled in your monitor's OSD menu")
            stdscr.addstr(5, 0, "Press any key to exit...")
            stdscr.refresh()
            stdscr.getch()
            return False
        
        stdscr.addstr(1, 0, f"Found {len(self.displays)} display(s)")
        stdscr.addstr(2, 0, "Reading brightness levels...")
        stdscr.refresh()
        
        # Get initial brightness values
        for i, display in enumerate(self.displays):
            current, max_val = self.get_brightness(display)
            self.current_brightness[display] = current
            self.max_brightness[display] = max_val
            self.target_brightness[display] = current
            self.last_sent_brightness[display] = current
            stdscr.addstr(3 + i, 2, f"Display {display}: {current}/{max_val}")
            stdscr.refresh()
        
        time.sleep(0.5)
        return True
    
    def draw_interface(self, stdscr):
        """Draw the main interface without flicker"""
        height, width = stdscr.getmaxyx()
        
        # Build the entire screen in memory first
        lines = []
        
        # Header
        header = "Brightness Control Center"
        lines.append(header.center(width - 1))
        lines.append("=" * min(width - 1, 40))
        lines.append("")
        
        # Controls
        lines.append("Controls:")
        lines.append(f"  [↑/→] Increase brightness (+{self.increment})")
        lines.append(f"  [↓/←] Decrease brightness (-{self.increment})")
        lines.append("  [+/-] Adjust step size")
        lines.append("  [0]   Control all displays")
        lines.append("  [1-9] Control specific display")
        lines.append("  [q/Esc] Quit")
        lines.append("")
        
        # Show selected display mode
        if self.selected_displays:
            selected_str = ", ".join(str(d) for d in self.selected_displays)
            lines.append(f"Mode: Controlling Display {selected_str}")
        else:
            lines.append("Mode: Controlling ALL displays")
        lines.append("")
        lines.append("-" * min(width - 1, 40))
        lines.append("")
        
        # Display brightness bars
        for display in self.displays:
            target = self.target_brightness[display]
            max_val = self.max_brightness[display]
            percent = int(target * 100 / max_val) if max_val > 0 else 0
            
            # Display label with selection indicator
            is_selected = not self.selected_displays or display in self.selected_displays
            label = f"Display {display}:"
            if is_selected:
                label = f"> {label}"
            else:
                label = f"  {label}"
            lines.append(label)
            
            # Progress bar
            bar_width = min(width - 20, 50)
            filled = int(target * bar_width / max_val) if max_val > 0 else 0
            
            bar = "[" + "#" * filled + "-" * (bar_width - filled) + "]"
            status = f"{percent:3d}% ({target}/{max_val})"
            
            # Add pending indicator if update hasn't been sent yet
            if target != self.last_sent_brightness.get(display, target):
                status += " *"
            
            lines.append(f"    {bar} {status}")
            lines.append("")
        
        # Footer
        lines.append(f"Step: {self.increment}")
        
        # Draw all at once using erase() instead of clear()
        stdscr.erase()  # This is faster than clear()
        for i, line in enumerate(lines):
            if i < height - 1:
                try:
                    stdscr.addstr(i, 0, line[:width-1])
                except:
                    pass
        
        stdscr.refresh()
    
    def adjust_brightness(self, delta: int):
        """Adjust brightness for selected displays"""
        with self.update_lock:
            # Determine which displays to adjust
            displays_to_adjust = self.selected_displays if self.selected_displays else self.displays
            
            for display in displays_to_adjust:
                new_val = self.target_brightness[display] + delta
                new_val = max(0, min(new_val, self.max_brightness[display]))
                self.target_brightness[display] = new_val
                self.current_brightness[display] = new_val  # Update UI immediately
    
    def run(self, stdscr):
        """Main application loop"""
        # Setup curses for smooth rendering
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(True)  # Non-blocking input
        stdscr.timeout(50)  # 50ms timeout for responsive feel
        
        # Disable curses delay for escape sequences
        os.environ.setdefault('ESCDELAY', '25')
        
        # Initialize displays
        if not self.init_displays(stdscr):
            return
        
        # Start background worker
        worker = threading.Thread(target=self.brightness_worker, daemon=True)
        worker.start()
        
        # Track last draw time to limit refresh rate
        last_draw = 0
        draw_interval = 0.05  # 20 FPS max
        
        # Main loop
        while True:
            current_time = time.time()
            
            # Only redraw at controlled rate
            if current_time - last_draw >= draw_interval:
                self.draw_interface(stdscr)
                last_draw = current_time
            
            try:
                key = stdscr.getch()
                
                if key == ord('q') or key == ord('Q') or key == 27:  # 27 is ESC
                    break
                elif key == curses.KEY_UP or key == curses.KEY_RIGHT:
                    self.adjust_brightness(self.increment)
                elif key == curses.KEY_DOWN or key == curses.KEY_LEFT:
                    self.adjust_brightness(-self.increment)
                elif key == ord('+') or key == ord('='):
                    self.increment = min(25, self.increment + 1)
                elif key == ord('-') or key == ord('_'):
                    self.increment = max(1, self.increment - 1)
                elif key == ord('0'):
                    # Select all displays
                    self.selected_displays = []
                elif ord('1') <= key <= ord('9'):
                    # Select specific display
                    display_num = key - ord('0')
                    if display_num in self.displays:
                        self.selected_displays = [display_num]
                    
            except KeyboardInterrupt:
                break
            except:
                pass
        
        # Cleanup
        self.running = False
        worker.join(timeout=0.5)

def main():
    # Check for ddcutil
    try:
        subprocess.run(["which", "ddcutil"], capture_output=True, check=True)
    except:
        print("Error: ddcutil is not installed")
        print("Install with: sudo pacman -S ddcutil")
        print("Setup: sudo modprobe i2c-dev && sudo usermod -aG i2c $USER")
        sys.exit(1)
    
    # Run the controller
    controller = BrightnessController()
    try:
        curses.wrapper(controller.run)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
