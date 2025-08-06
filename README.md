# Monitor Settings

[![CI](https://github.com/knowlen/monitorsettings/actions/workflows/ci.yml/badge.svg)](https://github.com/knowlen/monitorsettings/actions/workflows/ci.yml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: WTFPL](https://img.shields.io/badge/License-WTFPL-brightgreen.svg)](http://www.wtfpl.net/about/)

Terminal-based monitor control utility for Linux systems using DDC/CI protocol.

![Demo](assets/demo.gif)



## Features

- Real-time brightness control with visual progress bars
- Control all monitors simultaneously or individually
- Keyboard navigation with arrow keys
- Debounced DDC commands for responsive performance
- Two UI modes: inline (blessed) and full-screen (curses)
- Support for multiple monitors
- Extensible architecture for future monitor settings

## System Requirements

- Linux (tested on Arch Linux)
- Python 3.8+
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

#### From Source (Development)

```bash
# Clone this repository
git clone https://github.com/knowlen/monitorsettings.git
cd monitorsettings

# Install in development mode with blessed UI (recommended)
pip install -e ".[blessed]"

# Or without blessed (curses-only mode)
pip install -e .

# For development with all tools
pip install -e ".[blessed,dev]"
```

#### From PyPI (Coming Soon)

```bash
# Install with blessed UI (recommended)
pip install monitorsettings[blessed]

# Or basic installation (curses-only)
pip install monitorsettings
```

## Usage

```bash
# Run the monitor settings controller
monitorsettings

# Or use Python module syntax
python -m monitorsettings
```

### Controls

| Key(s) | Action |
|--------|--------|
| ↑/→ | Increase brightness |
| ↓/← | Decrease brightness |
| +/- | Adjust step size |
| 0 | Control all displays |
| 1-9 | Control specific display |
| q/Esc | Quit |

## Monitor Setup

DDC/CI must be enabled in your monitor's OSD menu. Look for settings named:
- DDC/CI
- DDC
- Display Data Channel

## Troubleshooting

### No monitors detected
- Ensure DDC/CI is enabled in monitor OSD
- Check i2c-dev module: `lsmod | grep i2c_dev`
- Verify i2c group membership: `groups | grep i2c`
- Some video cables don't support DDC

### Slow response
DDC/CI protocol limitation. Response times vary by monitor model.

### Permission errors
- Add user to i2c group: `sudo usermod -aG i2c $USER`
- Log out and back in for group changes
- Load i2c-dev module: `sudo modprobe i2c-dev`

## Architecture

- Modular design with pluggable UI backends (blessed/curses)
- Async DDC command processing with debouncing
- Extensible for additional monitor settings (color temperature, contrast, etc.)
- VCP code 0x10 for brightness control

### Communication Stack

```
monitorsettings (this app)
      ↓
ddcutil (user-space tool)
      ↓
/dev/i2c-X (created by i2c-dev)
      ↓
Graphics card I²C bus
      ↓
Monitor DDC/CI interface
```

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[blessed,dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=monitorsettings

# Run linters
black --check monitorsettings tests
ruff check monitorsettings tests
mypy monitorsettings
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

## Planned Features

- Color temperature adjustment
- Contrast and saturation controls
- Input source switching
- Profile management
- Configuration file support
- Preset profiles

## Contributing

Contributions are welcome! Please ensure all tests pass and code is formatted with black before submitting a PR.

## License

WTFPL - Do What The F*ck You Want To Public License
