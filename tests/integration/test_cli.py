"""
Integration tests for CLI entry point
"""

from unittest.mock import MagicMock

import pytest

from monitorsettings.cli import check_ddcutil, print_setup_instructions


class TestCLI:
    """Test cases for CLI functionality"""

    def test_check_ddcutil_available(self, mocker):
        """Test ddcutil check when available"""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0)

        result = check_ddcutil()

        assert result is True

    def test_check_ddcutil_not_available(self, mocker):
        """Test ddcutil check when not available"""
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = FileNotFoundError()

        result = check_ddcutil()

        assert result is False

    def test_print_setup_instructions(self, capsys):
        """Test setup instructions output"""
        print_setup_instructions()

        captured = capsys.readouterr()
        assert "ddcutil is not installed" in captured.out
        assert "sudo pacman -S ddcutil" in captured.out
        assert "sudo modprobe i2c-dev" in captured.out

    def test_main_no_ddcutil(self, mocker):
        """Test main when ddcutil is not available"""
        mocker.patch("monitorsettings.cli.check_ddcutil", return_value=False)
        mocker.patch("monitorsettings.cli.print_setup_instructions")

        from monitorsettings.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    def test_main_with_blessed(self, mocker):
        """Test main with blessed available"""
        mocker.patch("monitorsettings.cli.check_ddcutil", return_value=True)

        # Mock blessed controller
        mock_controller = MagicMock()
        mock_controller.run = MagicMock()

        mocker.patch(
            "monitorsettings.controllers.backlight.blessed.BlessedBacklightController",
            return_value=mock_controller,
        )

        from monitorsettings.cli import main

        main()

        mock_controller.run.assert_called_once()

    def test_main_keyboard_interrupt(self, mocker, capsys):
        """Test main handles KeyboardInterrupt gracefully"""
        mocker.patch("monitorsettings.cli.check_ddcutil", return_value=True)

        mock_controller = MagicMock()
        mock_controller.run.side_effect = KeyboardInterrupt()

        mocker.patch(
            "monitorsettings.controllers.backlight.blessed.BlessedBacklightController",
            return_value=mock_controller,
        )

        from monitorsettings.cli import main

        main()  # Should not raise, just print message

        captured = capsys.readouterr()
        assert "Interrupted by user" in captured.out
