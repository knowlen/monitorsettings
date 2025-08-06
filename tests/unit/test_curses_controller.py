"""
Unit tests for curses backlight controller using pytest
"""

import curses
from unittest.mock import MagicMock

import pytest

from monitorsettings.controllers.backlight.curses import CursesBacklightController


@pytest.fixture
def controller():
    """Fixture providing a CursesBacklightController instance"""
    return CursesBacklightController()


@pytest.fixture
def mock_stdscr():
    """Mock curses window object"""
    stdscr = MagicMock()
    stdscr.getmaxyx.return_value = (24, 80)  # Standard terminal size
    return stdscr


class TestCursesBacklightController:
    """Test cases for CursesBacklightController"""
    
    def test_initialization(self, controller):
        """Test controller initialization"""
        assert controller.stdscr is None
        assert controller.last_sent_brightness == {}
        assert controller.running is True
    
    def test_run_calls_wrapper(self, controller, mocker):
        """Test that run method uses curses wrapper"""
        mock_wrapper = mocker.patch('curses.wrapper')
        
        controller.run()
        
        mock_wrapper.assert_called_once()
    
    def test_handle_key_quit_q(self, controller):
        """Test quit with 'q' key"""
        controller.running = True
        
        controller.handle_key(ord('q'))
        
        assert controller.running is False
    
    def test_handle_key_quit_escape(self, controller):
        """Test quit with ESC key"""
        controller.running = True
        
        controller.handle_key(27)  # ESC
        
        assert controller.running is False
    
    @pytest.mark.parametrize("key,expected_delta", [
        (curses.KEY_UP, 10),
        (curses.KEY_RIGHT, 10),
        (curses.KEY_DOWN, -10),
        (curses.KEY_LEFT, -10),
    ])
    def test_handle_key_brightness_adjustment(self, controller, mocker, key, expected_delta):
        """Test brightness adjustment with arrow keys"""
        controller.increment = 10
        mock_adjust = mocker.patch.object(controller, 'adjust_brightness')
        
        controller.handle_key(key)
        
        mock_adjust.assert_called_once_with(expected_delta)
    
    @pytest.mark.parametrize("key,expected_change", [
        (ord('+'), 1),
        (ord('='), 1),
        (ord('-'), -1),
        (ord('_'), -1),
    ])
    def test_handle_key_step_adjustment(self, controller, key, expected_change):
        """Test step size adjustment"""
        controller.increment = 5
        
        controller.handle_key(key)
        
        assert controller.increment == 5 + expected_change
    
    def test_handle_key_step_limits(self, controller):
        """Test step size limits"""
        # Test upper limit
        controller.increment = 25
        controller.handle_key(ord('+'))
        assert controller.increment == 25  # Should stay at max
        
        # Test lower limit
        controller.increment = 1
        controller.handle_key(ord('-'))
        assert controller.increment == 1  # Should stay at min
    
    def test_handle_key_display_selection_all(self, controller, mocker):
        """Test selecting all displays with '0' key"""
        mock_select = mocker.patch.object(controller, 'select_display')
        
        controller.handle_key(ord('0'))
        
        mock_select.assert_called_once_with(None)
    
    @pytest.mark.parametrize("key_char,display_num", [
        ('1', 1),
        ('2', 2),
        ('5', 5),
        ('9', 9),
    ])
    def test_handle_key_display_selection_specific(self, controller, mocker, key_char, display_num):
        """Test selecting specific display with number keys"""
        mock_select = mocker.patch.object(controller, 'select_display')
        
        controller.handle_key(ord(key_char))
        
        mock_select.assert_called_once_with(display_num)
    
    def test_init_displays_failure(self, controller, mocker, mock_stdscr):
        """Test display initialization failure handling"""
        controller.stdscr = mock_stdscr
        mock_init = mocker.patch.object(controller, 'initialize', return_value=False)
        
        result = controller._init_displays()
        
        assert result is False
        # Should show error message
        mock_stdscr.addstr.assert_any_call(2, 0, "Error: No DDC/CI capable displays detected")
    
    def test_init_displays_success(self, controller, mocker, mock_stdscr):
        """Test successful display initialization"""
        controller.stdscr = mock_stdscr
        mock_init = mocker.patch.object(controller, 'initialize', return_value=True)
        controller.displays = [1, 2]
        controller.current_brightness = {1: 50, 2: 60}
        controller.max_brightness = {1: 100, 2: 100}
        
        result = controller._init_displays()
        
        assert result is True
        # Should show found displays
        mock_stdscr.addstr.assert_any_call(1, 0, "Found 2 display(s)")
    
    def test_draw_interface(self, controller, mock_stdscr):
        """Test interface drawing"""
        controller.stdscr = mock_stdscr
        controller.displays = [1, 2]
        controller.target_brightness = {1: 50, 2: 75}
        controller.max_brightness = {1: 100, 2: 100}
        controller.last_sent_brightness = {1: 50, 2: 75}
        controller.selected_displays = []
        controller.increment = 5
        
        controller.draw_interface()
        
        # Should clear screen and add content
        mock_stdscr.erase.assert_called_once()
        mock_stdscr.refresh.assert_called_once()
        assert mock_stdscr.addstr.called
    
    def test_draw_interface_with_selection(self, controller, mock_stdscr):
        """Test interface drawing with display selection"""
        controller.stdscr = mock_stdscr
        controller.displays = [1, 2]
        controller.target_brightness = {1: 50, 2: 75}
        controller.max_brightness = {1: 100, 2: 100}
        controller.last_sent_brightness = {1: 50, 2: 75}
        controller.selected_displays = [1]  # Only display 1 selected
        
        controller.draw_interface()
        
        # Should show selection mode
        calls = [str(call) for call in mock_stdscr.addstr.call_args_list]
        assert any("Controlling Display 1" in str(call) for call in calls)
    
    def test_draw_interface_pending_indicator(self, controller, mock_stdscr):
        """Test that pending changes show indicator"""
        controller.stdscr = mock_stdscr
        controller.displays = [1]
        controller.target_brightness = {1: 60}
        controller.max_brightness = {1: 100}
        controller.last_sent_brightness = {1: 50}  # Different from target
        controller.worker = MagicMock()
        controller.worker._last_sent = {}
        
        controller.draw_interface()
        
        # Should show pending indicator (*)
        calls = [str(call) for call in mock_stdscr.addstr.call_args_list]
        assert any("*" in str(call) for call in calls)
    
    def test_cleanup(self, controller, mocker):
        """Test cleanup on exit"""
        mock_stop = mocker.patch.object(controller, 'stop_worker')
        
        controller.cleanup()
        
        mock_stop.assert_called_once()