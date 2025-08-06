# Brightness Control

An interactive terminal-based monitor brightness controller for Linux systems using DDC/CI protocol.

## Features

- Real-time brightness control with visual progress bars
- Control all monitors simultaneously or individually
- Keyboard navigation with arrow keys
- Debounced DDC commands for responsive performance
- No flicker interface with smooth updates
- Support for multiple monitors

## System Requirements

- Linux (tested on Arch Linux)
- Python 3.7+
- `ddcutil` - DDC/CI monitor control utility
- Monitors with DDC/CI support enabled

## Installation

### System Dependencies

First, install `ddcutil`:

```bash
# Arch Linux
sudo pacman -S ddcutil

# Ubuntu/Debian
sudo apt-get install ddcutil

# Fedora
sudo dnf install ddcutil
```

### Setup DDC/CI Access

1. Load the i2c kernel module:
```bash
sudo modprobe i2c-dev
```

2. Make it persistent across reboots:
```bash
echo 'i2c-dev' | sudo tee /etc/modules-load.d/i2c-dev.conf
```

3. Add your user to the i2c group:
```bash
sudo usermod -aG i2c $USER
```

4. Log out and back in for group changes to take effect.

### Python Package Installation

#### Using uv (recommended - faster):
```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone or download this repository
cd screen_control

# Install with uv
uv pip install -e .

# Or create a venv and install
uv venv
source .venv/bin/activate  # On Linux/Mac
uv pip install -e .
```

#### Using pip (traditional):
```bash
# Clone or download this repository
cd screen_control

# Install in development mode
pip install -e .

# Or install normally
pip install .
```

## Usage

Run the brightness controller:
```bash
brightness-control
```

Or run directly without installation:
```bash
python brightness_control.py
```

### Controls

- **↑/→** - Increase brightness
- **↓/←** - Decrease brightness
- **+/-** - Adjust step size (how much brightness changes per keypress)
- **0** - Control all displays simultaneously
- **1-9** - Control specific display by number
- **q/Esc** - Quit the application

### Visual Indicators

- **>** - Arrow indicates which displays are being controlled
- **Progress Bar** - Shows current brightness level
- **Percentage** - Displays exact brightness value
- **\*** - Asterisk indicates pending brightness change

## Monitor Setup

**IMPORTANT**: DDC/CI must be enabled in your monitor's OSD (On-Screen Display) menu. This setting is usually found under:
- System Settings
- General Settings
- Display Settings
- Other Settings

Look for options like:
- DDC/CI
- DDC
- Display Data Channel

## Troubleshooting

### No monitors detected
1. Ensure DDC/CI is enabled in monitor OSD
2. Check if i2c-dev module is loaded: `lsmod | grep i2c_dev`
3. Verify user is in i2c group: `groups | grep i2c`
4. Try different video cables (some don't support DDC)
5. Check dmesg for i2c errors: `dmesg | grep i2c`

### Slow response times
This is a limitation of the DDC/CI protocol and ddcutil. The script uses debouncing and parallel commands to minimize delays, but hardware response times vary by monitor model.

### Permission errors
Make sure you've:
1. Added your user to the i2c group
2. Logged out and back in after group change
3. Loaded the i2c-dev kernel module

## Technical Details

The brightness controller uses:
- Python's `curses` library for terminal UI
- `ddcutil` for DDC/CI communication
- Threading for asynchronous brightness updates
- Debouncing to prevent command flooding
- VCP code 0x10 for brightness control

## License

MIT License

## Contributing

Feel free to open issues or submit pull requests for improvements.