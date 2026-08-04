import unittest
from unittest.mock import MagicMock, patch
import sys
import io

# Setup/Get the ctypes mock from sys.modules if it exists
if 'ctypes' in sys.modules:
    mock_ctypes = sys.modules['ctypes']
    if not isinstance(mock_ctypes, MagicMock):
        mock_ctypes = MagicMock()
        sys.modules['ctypes'] = mock_ctypes
else:
    mock_ctypes = MagicMock()
    sys.modules['ctypes'] = mock_ctypes

# Mock mido module so we don't need real MIDI devices
mock_mido = MagicMock()
# mido.open_input returns a list to make the message loop exit immediately
mock_mido.open_input.return_value = []
sys.modules['mido'] = mock_mido

# Also mock rtmidi to prevent package conflict checks
sys.modules['rtmidi'] = MagicMock()

import midi_to_input

class TestMidiToInput(unittest.TestCase):
    def setUp(self):
        # Always reset mock_ctypes to ensure isolated test environment
        mock_ctypes.reset_mock()

    @patch('sys.platform', 'win32')
    @patch('argparse.ArgumentParser.parse_args')
    @patch('midi_to_input.is_admin', return_value=True)
    def test_window_minimization_win32(self, mock_is_admin, mock_parse_args):
        # Setup mock arguments to bypass elevation and direct port loop
        mock_args = MagicMock()
        mock_args.port = 'MockPort'
        mock_args.threshold = 1.0
        mock_args.no_elevate = True
        mock_parse_args.return_value = mock_args

        # Mock user32 and kernel32
        mock_ctypes.windll.kernel32.GetConsoleWindow.return_value = 789
        mock_ctypes.windll.user32.ShowWindow = MagicMock()

        # Run script with stdout suppressed
        with patch('sys.stdout', new=io.StringIO()):
            midi_to_input.run_script()

        # Check console window was retrieved and ShowWindow(789, 6) was called
        mock_ctypes.windll.kernel32.GetConsoleWindow.assert_called_once()
        mock_ctypes.windll.user32.ShowWindow.assert_called_with(789, 6)

    @patch('sys.platform', 'linux')
    @patch('argparse.ArgumentParser.parse_args')
    def test_window_minimization_non_win32(self, mock_parse_args):
        # Setup mock arguments
        mock_args = MagicMock()
        mock_args.port = 'MockPort'
        mock_args.threshold = 1.0
        mock_args.no_elevate = True
        mock_parse_args.return_value = mock_args

        # Run script with stdout suppressed
        with patch('sys.stdout', new=io.StringIO()):
            midi_to_input.run_script()

        # GetConsoleWindow should not be called on Linux
        mock_ctypes.windll.kernel32.GetConsoleWindow.assert_not_called()
        mock_ctypes.windll.user32.ShowWindow.assert_not_called()

if __name__ == '__main__':
    unittest.main()
