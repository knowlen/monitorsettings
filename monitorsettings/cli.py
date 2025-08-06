"""
Main CLI entry point for monitor settings control
"""

import subprocess
import sys


def check_ddcutil() -> bool:
    """Check if ddcutil is available on the system"""
    try:
        subprocess.run(["which", "ddcutil"], capture_output=True, check=True, timeout=2)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def print_setup_instructions():
    """Print setup instructions for ddcutil"""
    print("Error: ddcutil is not installed")
    print("\nInstallation:")
    print("  Arch Linux:    sudo pacman -S ddcutil")
    print("  Ubuntu/Debian: sudo apt-get install ddcutil")
    print("  Fedora:        sudo dnf install ddcutil")
    print("\nSetup:")
    print("  1. Load i2c module: sudo modprobe i2c-dev")
    print("  2. Add to startup:  echo 'i2c-dev' | sudo tee /etc/modules-load.d/i2c-dev.conf")
    print("  3. Add user to i2c: sudo usermod -aG i2c $USER")
    print("  4. Log out and back in for group changes to take effect")
    print("\nNote: DDC/CI must be enabled in your monitor's OSD menu")


def main():
    """Main entry point for the monitor settings CLI"""

    # Check for ddcutil first
    if not check_ddcutil():
        print_setup_instructions()
        sys.exit(1)

    # Try to use blessed controller first, fall back to curses if unavailable
    controller = None

    try:
        # Try importing blessed controller
        from .controllers.backlight.blessed import BlessedBacklightController

        controller = BlessedBacklightController()
    except ImportError:
        # Fall back to curses controller
        try:
            from .controllers.backlight.curses import CursesBacklightController

            controller = CursesBacklightController()
        except ImportError as e:
            print(f"Error: Could not import any controller: {e}")
            sys.exit(1)

    # Run the controller
    try:
        controller.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
