"""
Unit tests for blessed backlight controller using pytest
"""

from unittest.mock import MagicMock

import pytest

from monitorsettings.controllers.backlight.blessed import BlessedBacklightController


@pytest.fixture
def mock_terminal(mocker):
    """Mock blessed Terminal"""
    mock_term = MagicMock()
    mock_term.cbreak.return_value.__enter__ = MagicMock(return_value=None)
    mock_term.cbreak.return_value.__exit__ = MagicMock(return_value=None)
    mock_term.hidden_cursor.return_value.__enter__ = MagicMock(return_value=None)
    mock_term.hidden_cursor.return_value.__exit__ = MagicMock(return_value=None)
    mocker.patch('monitorsettings.controllers.backlight.blessed.Terminal', return_value=mock_term)
    return mock_term


@pytest.fixture
def controller(mock_terminal):
    """Fixture providing a BlessedBacklightController instance"""
    return BlessedBacklightController()


class TestBlessedBacklightController:
    """Test cases for BlessedBacklightController"""
    
    def test_initialization(self, controller, mock_terminal):
        """Test controller initialization"""
        assert controller.term == mock_terminal
        assert controller.interface_lines == 0
        assert controller.last_sent_brightness == {}
        assert controller.running is True
    
    def test_initialization_failure(self, controller, mocker):
        """Test handling of initialization failure"""
        mock_init = mocker.patch.object(controller, 'initialize', return_value=False)
        mock_print = mocker.patch('builtins.print')
        mock_term = controller.term
        mock_term.red = lambda x: f"RED:{x}"
        
        controller.run()
        
        # Should print error message
        mock_print.assert_called()
        # Check that error message was printed
        error_printed = False
        for call in mock_print.call_args_list:
            if call.args and ('No DDC/CI capable displays detected' in str(call.args[0]) or 
                            'RED:Error' in str(call.args[0])):
                error_printed = True
                break
        assert error_printed
    
    def test_handle_key_quit(self, controller):
        """Test quit key handling"""
        controller.running = True
        
        # Test 'q' key
        mock_key = MagicMock()
        mock_key.__str__ = lambda x: 'q'
        mock_key.__eq__ = lambda x, y: y == 'q'
        mock_key.name = None
        
        controller.handle_key(mock_key)
        assert controller.running is False
    
    def test_handle_key_escape(self, controller):
        """Test escape key handling"""
        controller.running = True
        
        mock_key = MagicMock()
        mock_key.name = 'KEY_ESCAPE'
        
        controller.handle_key(mock_key)
        assert controller.running is False
    
    @pytest.mark.parametrize("key_name,expected_delta", [
        ('KEY_RIGHT', 5),
        ('KEY_LEFT', -5),
    ])
    def test_handle_key_brightness_adjustment(self, controller, mocker, key_name, expected_delta):
        """Test brightness adjustment keys"""
        controller.increment = 5
        mock_adjust = mocker.patch.object(controller, 'adjust_brightness')
        
        mock_key = MagicMock()
        mock_key.name = key_name
        
        controller.handle_key(mock_key)
        mock_adjust.assert_called_once_with(expected_delta)
    
    def test_handle_key_step_increase(self, controller):
        """Test step size increase"""
        controller.increment = 5
        
        mock_key = MagicMock()
        mock_key.name = 'KEY_UP'
        
        controller.handle_key(mock_key)
        assert controller.increment == 6
    
    def test_handle_key_step_decrease(self, controller):
        """Test step size decrease"""
        controller.increment = 5
        
        mock_key = MagicMock()
        mock_key.name = 'KEY_DOWN'
        
        controller.handle_key(mock_key)
        assert controller.increment == 4
    
    def test_handle_key_step_limits(self, controller):
        """Test step size limits"""
        # Test upper limit
        controller.increment = 25
        mock_key = MagicMock()
        mock_key.name = 'KEY_UP'
        controller.handle_key(mock_key)
        assert controller.increment == 25  # Should stay at max
        
        # Test lower limit
        controller.increment = 1
        mock_key.name = 'KEY_DOWN'
        controller.handle_key(mock_key)
        assert controller.increment == 1  # Should stay at min
    
    def test_handle_key_display_selection_all(self, controller, mocker):
        """Test selecting all displays with '0' key"""
        mock_select = mocker.patch.object(controller, 'select_display')
        
        mock_key = MagicMock()
        mock_key.__str__ = lambda x: '0'
        mock_key.__eq__ = lambda x, y: y == '0'
        mock_key.isdigit = lambda: True
        mock_key.name = None
        
        controller.handle_key(mock_key)
        mock_select.assert_called_once_with(None)
    
    @pytest.mark.parametrize("key_char,display_num", [
        ('1', 1),
        ('2', 2),
        ('9', 9),
    ])
    def test_handle_key_display_selection_specific(self, controller, mocker, key_char, display_num):
        """Test selecting specific display with number keys"""
        mock_select = mocker.patch.object(controller, 'select_display')
        
        # Create a string-like mock that behaves properly for comparisons
        class MockKey:
            def __init__(self, char):
                self.char = char
                self.name = None
            def __str__(self):
                return self.char
            def __eq__(self, other):
                return str(self) == str(other)
            def __le__(self, other):
                return str(self) <= str(other)
            def __ge__(self, other):
                return str(self) >= str(other)
            def __int__(self):
                return int(self.char)
            def isdigit(self):
                return True
        
        mock_key = MockKey(key_char)
        controller.handle_key(mock_key)
        mock_select.assert_called_once_with(display_num)
    
    def test_cleanup(self, controller, mocker):
        """Test cleanup on exit"""
        mock_stop = mocker.patch.object(controller, 'stop_worker')
        mock_print = mocker.patch('builtins.print')
        controller.interface_lines = 5
        
        controller.cleanup()
        
        mock_stop.assert_called_once()
        # Should print cleanup message
        assert mock_print.called
    
    def test_draw_interface_color_setup(self, controller, mock_terminal, mocker):
        """Test that draw_interface sets up colors correctly"""
        controller.displays = [1]
        controller.target_brightness = {1: 50}
        controller.max_brightness = {1: 100}
        controller.last_sent_brightness = {1: 50}
        controller.selected_displays = []
        controller.worker = MagicMock()
        controller.worker._last_sent = {}
        
        mock_print = mocker.patch('builtins.print')
        controller.draw_interface()
        
        # Check that color methods were called
        assert mock_terminal.color_rgb.called
        assert mock_terminal.clear_eol
    
    def test_draw_interface_updates_line_count(self, controller, mocker):
        """Test that draw_interface updates the line count"""
        controller.displays = [1, 2]
        controller.target_brightness = {1: 50, 2: 75}
        controller.max_brightness = {1: 100, 2: 100}
        controller.last_sent_brightness = {1: 50, 2: 75}
        controller.worker = MagicMock()
        controller.worker._last_sent = {}
        
        mocker.patch('builtins.print')
        controller.draw_interface()
        
        assert controller.interface_lines > 0