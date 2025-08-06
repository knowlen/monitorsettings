"""
Blessed-based backlight controller with inline terminal UI
"""

import time
from typing import Dict

from blessed import Terminal

from .base import BacklightController


class BlessedBacklightController(BacklightController):
    """
    Backlight controller using blessed library for inline terminal updates.
    Does not take over the entire screen, updates in place.
    """

    def __init__(self):
        super().__init__()
        self.term = Terminal()
        self.interface_lines = 0
        self.last_sent_brightness: Dict[int, int] = {}

    def run(self):
        """Main run loop with blessed terminal handling"""
        print("Initializing brightness controller...")

        if not self.initialize():
            print(self.term.red("Error: No DDC/CI capable displays detected"))
            print("Make sure DDC/CI is enabled in your monitor's OSD menu")
            return

        print(f"Found {len(self.displays)} display(s)")
        print("Reading brightness levels...")

        # Show initial brightness
        for display in self.displays:
            current = self.current_brightness[display]
            max_val = self.max_brightness[display]
            self.last_sent_brightness[display] = current
            print(f"  Display {display}: {current}/{max_val}")

        print("\nStarting interactive mode...\n")
        time.sleep(1)

        # Start background worker
        self.start_worker()

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
                    self.handle_key(key)

        self.cleanup()

    def draw_interface(self):
        """Draw interface using blessed terminal with maroon/port color palette"""
        # Move cursor up to overwrite previous interface
        if self.interface_lines > 0:
            print(self.term.move_up * self.interface_lines, end="")

        lines = []

        # Color palette
        maroon = self.term.color_rgb(139, 69, 89)
        deep_wine = self.term.color_rgb(88, 44, 55)
        rose_gold = self.term.color_rgb(183, 110, 121)
        sage = self.term.color_rgb(87, 116, 90)
        warm_gray = self.term.color_rgb(120, 113, 108)
        cream = self.term.color_rgb(242, 234, 220)

        # Header
        lines.append(deep_wine("=" * 60))
        lines.append(maroon("       ") + cream(" Brightness Control ") + maroon("       "))
        lines.append(deep_wine("=" * 60))
        lines.append("")

        # Mode indicator
        if self.selected_displays:
            mode = f"Mode: Display {', '.join(str(d) for d in self.selected_displays)}"
        else:
            mode = "Mode: ALL displays"
        lines.append(rose_gold(mode) + warm_gray(" | ") + cream(f"Step: {self.increment}"))
        lines.append("")

        # Display bars
        for display in self.displays:
            target = self.target_brightness[display]
            max_val = self.max_brightness[display]
            percent = int(target * 100 / max_val) if max_val > 0 else 0

            # Selection indicator
            is_selected = not self.selected_displays or display in self.selected_displays
            indicator = rose_gold(">") if is_selected else warm_gray(" ")

            # Progress bar
            bar_width = 40
            filled = int(target * bar_width / max_val) if max_val > 0 else 0

            filled_bar = rose_gold("█" * filled)
            empty_bar = warm_gray("·" * (bar_width - filled))

            # Pending indicator
            pending = sage("*") if target != self.last_sent_brightness.get(display, target) else " "

            # Update last sent for UI purposes
            if target == self.worker._last_sent.get((display, self.BRIGHTNESS_VCP_CODE), -1):
                self.last_sent_brightness[display] = target

            # Compose line
            display_text = cream(f"Display {display}:")
            percent_text = rose_gold(f"{percent:3d}%")
            lines.append(
                f"{indicator} {display_text} [{filled_bar}{empty_bar}] {percent_text} {pending}"
            )

        lines.append("")
        lines.append(warm_gray("-" * 60))
        lines.append(
            warm_gray("[")
            + cream("←/→")
            + warm_gray("] Brightness  [")
            + cream("↑/↓")
            + warm_gray("] Step size  [")
            + cream("0-9")
            + warm_gray("] Select  [")
            + cream("q/ESC")
            + warm_gray("] Quit")
        )

        # Print all lines, clearing to end of line for each
        for line in lines:
            print(line + self.term.clear_eol)

        self.interface_lines = len(lines)

    def handle_key(self, key):
        """Handle keyboard input"""
        if key == "q" or key == "Q" or key.name == "KEY_ESCAPE":
            self.running = False
        elif key.name == "KEY_RIGHT":
            self.adjust_brightness(self.increment)
        elif key.name == "KEY_LEFT":
            self.adjust_brightness(-self.increment)
        elif key.name == "KEY_UP":
            self.increment = min(25, self.increment + 1)
        elif key.name == "KEY_DOWN":
            self.increment = max(1, self.increment - 1)
        elif key in ["+", "="]:
            self.increment = min(25, self.increment + 1)
        elif key in ["-", "_"]:
            self.increment = max(1, self.increment - 1)
        elif key == "0":
            self.select_display(None)
        elif key.isdigit() and "1" <= key <= "9":
            self.select_display(int(key))

    def cleanup(self):
        """Clean up on exit"""
        self.stop_worker()

        # Clear the interface area
        if self.interface_lines > 0:
            print(self.term.move_up * self.interface_lines, end="")
            for _ in range(self.interface_lines):
                print(self.term.clear_eol)
            print(self.term.move_up * self.interface_lines, end="")

        print("\nBrightness controller exited.")
