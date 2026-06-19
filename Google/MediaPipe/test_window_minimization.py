import unittest
from unittest.mock import MagicMock, patch
import sys
import io

# Mocking dependencies that might not be present or cause issues on Linux/headless
sys.modules['cv2'] = MagicMock()
sys.modules['mediapipe'] = MagicMock()
sys.modules['mediapipe.tasks'] = MagicMock()
sys.modules['mediapipe.tasks.python'] = MagicMock()
sys.modules['mediapipe.tasks.python.vision'] = MagicMock()
sys.modules['numpy'] = MagicMock()
sys.modules['pythonosc'] = MagicMock()
sys.modules['pythonosc.udp_client'] = MagicMock()

# Mock ctypes before importing the module
mock_ctypes = MagicMock()
sys.modules['ctypes'] = mock_ctypes

import Google.MediaPipe.mediapipe_osc as mediapipe_osc

class TestWindowMinimization(unittest.TestCase):
    @patch('sys.platform', 'win32')
    @patch('cv2.VideoCapture')
    @patch('cv2.namedWindow')
    @patch('cv2.resizeWindow')
    @patch('cv2.setMouseCallback')
    @patch('Google.MediaPipe.mediapipe_osc.setup_detectors')
    @patch('builtins.input', return_value='')
    def test_minimization_logic(self, mock_input, mock_setup_detectors, mock_set_mouse, mock_resize, mock_named_win, mock_video_cap):

        # Setup mocks
        mock_ctypes.windll.user32.FindWindowW.return_value = 123  # Mock UI HWND
        mock_ctypes.windll.kernel32.GetConsoleWindow.return_value = 456  # Mock Console HWND

        # Mock VideoCapture to return an object that IS opened
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        # Make it fail on first read to exit loop
        mock_cap.read.return_value = (False, None)
        mock_video_cap.return_value = mock_cap

        # Mock setup_detectors to return dummy objects
        mock_setup_detectors.return_value = (MagicMock(), MagicMock())

        # Suppress stdout to avoid clutter
        with patch('sys.stdout', new=io.StringIO()):
            # Execute main
            mediapipe_osc.main()

        # Verify UI window minimization
        mock_ctypes.windll.user32.FindWindowW.assert_called_once_with(None, 'Google MediaPipe')
        mock_ctypes.windll.user32.ShowWindow.assert_any_call(123, 6)

        # Verify Console window minimization
        mock_ctypes.windll.kernel32.GetConsoleWindow.assert_called_once()
        mock_ctypes.windll.user32.ShowWindow.assert_any_call(456, 6)

if __name__ == '__main__':
    unittest.main()
