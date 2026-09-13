import os
import sys
import unittest
from unittest.mock import MagicMock, patch

dir_path = os.path.dirname(os.path.abspath(__file__))
if dir_path not in sys.path:
    sys.path.insert(0, dir_path)

import tobii_osc

class TestTobiiOscWinGaze(unittest.TestCase):

    def setUp(self):
        tobii_osc.stats['total_frames'] = 0
        tobii_osc.stats['valid_left'] = 0
        tobii_osc.stats['valid_right'] = 0
        tobii_osc.stats['valid_avg'] = 0
        tobii_osc.stats['mouse_moves'] = 0
        tobii_osc.stats['mouse_errors'] = 0
        tobii_osc.stats['last_error'] = None

    def test_set_cursor_pos_fallback(self):
        with patch('sys.platform', 'linux'):
            with patch('tobii_osc.mouse_controller') as mock_mc:
                mock_mc.position = (0, 0)
                res = tobii_osc.set_cursor_pos(100, 200)
                self.assertTrue(res)
                self.assertEqual(mock_mc.position, (100, 200))

    @patch('tobii_osc.HAS_WINSDK_GAZE', True)
    @patch('sys.platform', 'win32')
    def test_run_windows_gaze_success(self):
        mock_client = MagicMock()
        mock_gaze_source = MagicMock()
        mock_token = "dummy_token"
        mock_gaze_source.add_gaze_moved.return_value = mock_token

        mock_win_preview = MagicMock()
        mock_win_preview.GazeInputSourcePreview.get_for_current_view.return_value = mock_gaze_source

        with patch('tobii_osc.win_gaze_preview', mock_win_preview):
            with patch('tobii_osc.set_cursor_pos') as mock_set_cursor:
                mock_set_cursor.return_value = True
                result = tobii_osc.run_windows_gaze(mock_client, move_mouse=True, screen_size=(1920, 1080), debug=False)

                self.assertIsNotNone(result)
                self.assertEqual(result, (mock_gaze_source, mock_token))
                mock_gaze_source.add_gaze_moved.assert_called_once()

                callback_func = mock_gaze_source.add_gaze_moved.call_args[0][0]

                mock_args = MagicMock()
                mock_point = MagicMock()
                mock_eye_pos = MagicMock()
                mock_eye_pos.x = 960.0
                mock_eye_pos.y = 540.0
                mock_point.point = mock_eye_pos
                mock_args.current_point = mock_point

                callback_func(None, mock_args)
                mock_set_cursor.assert_called_with(960.0, 540.0)
                mock_client.send_message.assert_any_call("/Tobii/gaze_x", 0.5)
                mock_client.send_message.assert_any_call("/Tobii/gaze_y", 0.5)

    @patch('tobii_osc.HAS_WINSDK_GAZE', True)
    @patch('sys.platform', 'win32')
    def test_run_windows_gaze_element_not_found(self):
        mock_win_preview = MagicMock()
        mock_win_preview.GazeInputSourcePreview.get_for_current_view.side_effect = Exception("0x80070490 Element not found")

        with patch('tobii_osc.win_gaze_preview', mock_win_preview):
            res = tobii_osc.run_windows_gaze(MagicMock())
            self.assertIsNone(res)

    def test_run_windows_gaze_non_win32(self):
        with patch('sys.platform', 'linux'):
            res = tobii_osc.run_windows_gaze(MagicMock())
            self.assertIsNone(res)

if __name__ == '__main__':
    unittest.main()
