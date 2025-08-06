"""
Integration tests for UI fallback mechanism
"""

from unittest.mock import MagicMock

import pytest


class TestFallback:
    """Test cases for blessed to curses fallback"""

    def test_blessed_import_success(self, mocker):
        """Test successful blessed import and usage"""
        mocker.patch("monitorsettings.cli.check_ddcutil", return_value=True)

        mock_controller = MagicMock()
        mocker.patch(
            "monitorsettings.controllers.backlight.blessed.BlessedBacklightController",
            return_value=mock_controller,
        )

        from monitorsettings.cli import main

        main()

        mock_controller.run.assert_called_once()

    def test_curses_fallback(self, mocker):
        """Test fallback to curses when blessed fails"""
        mocker.patch("monitorsettings.cli.check_ddcutil", return_value=True)

        # Make blessed import fail
        mocker.patch(
            "monitorsettings.controllers.backlight.blessed.BlessedBacklightController",
            side_effect=ImportError("blessed not available"),
        )

        # Mock curses controller
        mock_controller = MagicMock()
        mocker.patch(
            "monitorsettings.controllers.backlight.curses.CursesBacklightController",
            return_value=mock_controller,
        )

        from monitorsettings.cli import main

        main()

        mock_controller.run.assert_called_once()

    def test_no_controllers_available(self, mocker):
        """Test error when both controllers are unavailable"""
        mocker.patch("monitorsettings.cli.check_ddcutil", return_value=True)

        # Make both imports fail
        mocker.patch(
            "monitorsettings.controllers.backlight.blessed.BlessedBacklightController",
            side_effect=ImportError("blessed not available"),
        )
        mocker.patch(
            "monitorsettings.controllers.backlight.curses.CursesBacklightController",
            side_effect=ImportError("curses not available"),
        )

        from monitorsettings.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
