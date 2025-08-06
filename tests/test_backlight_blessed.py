"""
Tests for blessed backlight controller
"""

import unittest
from unittest.mock import patch, MagicMock
from monitorsettings.controllers.backlight.blessed import BlessedBacklightController


class TestBlessedBacklightController(unittest.TestCase):
    """Test cases for BlessedBacklightController"""
    
    @patch('monitorsettings.controllers.backlight.blessed.Terminal')
    def setUp(self, mock_terminal):
        """Set up test fixtures"""
        self.mock_term = MagicMock()
        mock_terminal.return_value = self.mock_term
        self.controller = BlessedBacklightController()
    
    @patch.object(BlessedBacklightController, 'initialize')
    def test_initialization_failure(self, mock_init):
        """Test handling of initialization failure"""
        mock_init.return_value = False
        
        with patch('builtins.print') as mock_print:
            self.controller.run()
            
        # Should print error message
        calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any('No DDC/CI capable displays detected' in str(call) for call in calls))
    
    def test_handle_key_quit(self):
        """Test quit key handling"""
        self.controller.running = True
        
        # Create mock key with 'q' character
        mock_key = MagicMock()
        mock_key.__str__ = lambda x: 'q'
        mock_key.__eq__ = lambda x, y: y == 'q'
        mock_key.name = None
        
        self.controller.handle_key(mock_key)
        self.assertFalse(self.controller.running)
    
    def test_handle_key_brightness_adjustment(self):
        """Test brightness adjustment keys"""
        self.controller.displays = [1, 2]
        self.controller.target_brightness = {1: 50, 2: 60}
        self.controller.max_brightness = {1: 100, 2: 100}
        self.controller.increment = 5
        
        # Mock key for right arrow
        mock_key = MagicMock()
        mock_key.name = 'KEY_RIGHT'
        
        with patch.object(self.controller, 'adjust_brightness') as mock_adjust:
            self.controller.handle_key(mock_key)
            mock_adjust.assert_called_once_with(5)
    
    def test_handle_key_step_adjustment(self):
        """Test step size adjustment"""
        self.controller.increment = 5
        
        # Test increase
        mock_key = MagicMock()
        mock_key.name = 'KEY_UP'
        self.controller.handle_key(mock_key)
        self.assertEqual(self.controller.increment, 6)
        
        # Test decrease
        mock_key.name = 'KEY_DOWN'
        self.controller.handle_key(mock_key)
        self.assertEqual(self.controller.increment, 5)
    
    def test_handle_key_display_selection(self):
        """Test display selection keys"""
        self.controller.displays = [1, 2, 3]
        
        # Test select all (0 key)
        mock_key = MagicMock()
        mock_key.__str__ = lambda x: '0'
        mock_key.__eq__ = lambda x, y: y == '0'
        mock_key.isdigit = lambda: True
        mock_key.name = None
        
        self.controller.handle_key(mock_key)
        self.assertEqual(self.controller.selected_displays, [])
        
        # Test select specific display
        mock_key.__str__ = lambda x: '2'
        mock_key.__eq__ = lambda x, y: y == '2'
        mock_key.__int__ = lambda x: 2
        
        with patch.object(self.controller, 'select_display') as mock_select:
            self.controller.handle_key(mock_key)
            mock_select.assert_called_once_with(2)


if __name__ == '__main__':
    unittest.main()