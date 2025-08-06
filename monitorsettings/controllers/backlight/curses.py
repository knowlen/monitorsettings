"""
Curses-based backlight controller with full-screen terminal UI
"""

import curses
import os
import time
from typing import Any, Dict, Optional

from .base import BacklightController


class CursesBacklightController(BacklightController):
    """
    Backlight controller using curses library for full-screen terminal UI.
    Takes over the entire terminal screen like vim/nano.
    """

    def __init__(self) -> None:
        super().__init__()
        self.stdscr: Optional[Any] = None
        self.last_sent_brightness: Dict[int, int] = {}

    def run(self) -> None:
        """Main entry point that sets up curses wrapper"""
        try:
            curses.wrapper(self._run_curses)
        except KeyboardInterrupt:
            pass

    def _run_curses(self, stdscr: Any) -> None:
        """Main run loop with curses terminal handling"""
        self.stdscr = stdscr

        # Setup curses for smooth rendering
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(True)  # Non-blocking input
        stdscr.timeout(50)  # 50ms timeout for responsive feel

        # Disable curses delay for escape sequences
        os.environ.setdefault("ESCDELAY", "25")

        # Initialize displays
        if not self._init_displays():
            return

        # Initialize last sent brightness
        for display in self.displays:
            self.last_sent_brightness[display] = self.current_brightness[display]

        # Start background worker
        self.start_worker()

        # Track last draw time to limit refresh rate
        last_draw = 0.0
        draw_interval = 0.05  # 20 FPS max

        # Main loop
        while self.running:
            current_time = time.time()

            # Only redraw at controlled rate
            if current_time - last_draw >= draw_interval:
                self.draw_interface()
                last_draw = current_time

            try:
                key = stdscr.getch()
                self.handle_key(key)
            except KeyboardInterrupt:
                break
            except Exception:
                pass

        self.cleanup()

    def _init_displays(self) -> bool:
        """Initialize display detection and brightness reading"""
        assert self.stdscr is not None
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Detecting displays...")
        self.stdscr.refresh()

        if not self.initialize():
            self.stdscr.addstr(2, 0, "Error: No DDC/CI capable displays detected")
            self.stdscr.addstr(3, 0, "Make sure DDC/CI is enabled in your monitor's OSD menu")
            self.stdscr.addstr(5, 0, "Press any key to exit...")
            self.stdscr.refresh()
            self.stdscr.getch()
            return False

        self.stdscr.addstr(1, 0, f"Found {len(self.displays)} display(s)")
        self.stdscr.addstr(2, 0, "Reading brightness levels...")
        self.stdscr.refresh()

        # Show initial brightness values
        for i, display in enumerate(self.displays):
            current = self.current_brightness[display]
            max_val = self.max_brightness[display]
            self.stdscr.addstr(3 + i, 2, f"Display {display}: {current}/{max_val}")
            self.stdscr.refresh()

        time.sleep(0.5)
        return True

    def draw_interface(self) -> None:
        """Draw the main interface without flicker"""
        assert self.stdscr is not None
        height, width = self.stdscr.getmaxyx()

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
            else:
                # Update last sent for UI purposes
                if target == self.worker._last_sent.get((display, self.BRIGHTNESS_VCP_CODE), -1):
                    self.last_sent_brightness[display] = target

            lines.append(f"    {bar} {status}")
            lines.append("")

        # Footer
        lines.append(f"Step: {self.increment}")

        # Draw all at once using erase() instead of clear()
        self.stdscr.erase()  # This is faster than clear()
        for i, line in enumerate(lines):
            if i < height - 1:
                try:
                    self.stdscr.addstr(i, 0, line[: width - 1])
                except Exception:
                    pass

        self.stdscr.refresh()

    def handle_key(self, key: int) -> None:
        """Handle keyboard input"""
        if key == ord("q") or key == ord("Q") or key == 27:  # 27 is ESC
            self.running = False
        elif key == curses.KEY_UP or key == curses.KEY_RIGHT:
            self.adjust_brightness(self.increment)
        elif key == curses.KEY_DOWN or key == curses.KEY_LEFT:
            self.adjust_brightness(-self.increment)
        elif key == ord("+") or key == ord("="):
            self.increment = min(25, self.increment + 1)
        elif key == ord("-") or key == ord("_"):
            self.increment = max(1, self.increment - 1)
        elif key == ord("0"):
            self.select_display(None)
        elif ord("1") <= key <= ord("9"):
            display_num = key - ord("0")
            self.select_display(display_num)

    def cleanup(self) -> None:
        """Clean up on exit"""
        self.stop_worker()
