"""
Tests for curses backlight controller
"""

import unittest
from unittest.mock import patch, MagicMock
import curses
from monitorsettings.controllers.backlight.curses import CursesBacklightController


class TestCursesBacklightController(unittest.TestCase):
    """Test cases for CursesBacklightController"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.controller = CursesBacklightController()
    
    @patch('curses.wrapper')
    def test_run_calls_wrapper(self, mock_wrapper):
        """Test that run method uses curses wrapper"""
        self.controller.run()
        mock_wrapper.assert_called_once()
    
    def test_handle_key_quit(self):
        """Test quit key handling"""
        self.controller.running = True
        
        # Test 'q' key
        self.controller.handle_key(ord('q'))
        self.assertFalse(self.controller.running)
        
        # Reset and test ESC key
        self.controller.running = True
        self.controller.handle_key(27)  # ESC
        self.assertFalse(self.controller.running)
    
    def test_handle_key_brightness_adjustment(self):
        """Test brightness adjustment with arrow keys"""
        self.controller.displays = [1]
        self.controller.target_brightness = {1: 50}
        self.controller.max_brightness = {1: 100}
        self.controller.increment = 10
        
        with patch.object(self.controller, 'adjust_brightness') as mock_adjust:
            # Test UP arrow
            self.controller.handle_key(curses.KEY_UP)
            mock_adjust.assert_called_with(10)
            
            # Test DOWN arrow
            self.controller.handle_key(curses.KEY_DOWN)
            mock_adjust.assert_called_with(-10)
    
    def test_handle_key_step_adjustment(self):
        """Test step size adjustment"""
        self.controller.increment = 5
        
        # Test increase with '+'
        self.controller.handle_key(ord('+'))
        self.assertEqual(self.controller.increment, 6)
        
        # Test decrease with '-'
        self.controller.handle_key(ord('-'))
        self.assertEqual(self.controller.increment, 5)
        
        # Test limits
        self.controller.increment = 25
        self.controller.handle_key(ord('+'))
        self.assertEqual(self.controller.increment, 25)  # Should stay at max
        
        self.controller.increment = 1
        self.controller.handle_key(ord('-'))
        self.assertEqual(self.controller.increment, 1)  # Should stay at min
    
    def test_handle_key_display_selection(self):
        """Test display selection with number keys"""
        self.controller.displays = [1, 2, 3]
        
        # Test select all with '0'
        self.controller.handle_key(ord('0'))
        self.assertEqual(self.controller.selected_displays, [])
        
        # Test select specific display
        with patch.object(self.controller, 'select_display') as mock_select:
            self.controller.handle_key(ord('2'))
            mock_select.assert_called_once_with(2)
    
    @patch.object(CursesBacklightController, 'initialize')
    def test_init_displays_failure(self, mock_init):
        """Test display initialization failure handling"""
        mock_init.return_value = False
        mock_stdscr = MagicMock()
        
        result = self.controller._init_displays()
        self.assertFalse(result)
    
    @patch.object(CursesBacklightController, 'initialize')
    def test_init_displays_success(self, mock_init):
        """Test successful display initialization"""
        mock_init.return_value = True
        self.controller.displays = [1, 2]
        self.controller.current_brightness = {1: 50, 2: 60}
        self.controller.max_brightness = {1: 100, 2: 100}
        
        mock_stdscr = MagicMock()
        self.controller.stdscr = mock_stdscr
        
        result = self.controller._init_displays()
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()