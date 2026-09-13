import os
import sys
import math
import time
import socket
import unittest
from unittest.mock import MagicMock, patch
import ctypes

dir_path = os.path.dirname(os.path.abspath(__file__))
if dir_path not in sys.path:
    sys.path.insert(0, dir_path)

import tobii_4c_osc

class TestTobii4COsc(unittest.TestCase):

    def setUp(self):
        tobii_4c_osc.state.last_gaze_data = None
        tobii_4c_osc.state.last_head_pose_data = None
        tobii_4c_osc.state.client = MagicMock()
        for f in tobii_4c_osc.state.features:
            f.current_val = 0.0
            f.enabled = True

    def test_structures(self):
        gp = tobii_4c_osc.tobii_gaze_point_t()
        gp.timestamp_us = 1000
        gp.validity = tobii_4c_osc.TobiiValidity.TOBII_VALIDITY_VALID
        gp.position_xy[0] = 0.5
        gp.position_xy[1] = 0.25
        self.assertEqual(gp.timestamp_us, 1000)
        self.assertAlmostEqual(gp.position_xy[0], 0.5, places=5)

        gd = tobii_4c_osc.tobii_gaze_data_t()
        gd.timestamp_us = 2000
        gd.left_gaze_point_validity = tobii_4c_osc.TobiiValidity.TOBII_VALIDITY_VALID
        gd.left_gaze_point_on_display_normalized[0] = 0.4
        gd.left_gaze_point_on_display_normalized[1] = 0.6
        self.assertEqual(gd.timestamp_us, 2000)
        self.assertAlmostEqual(gd.left_gaze_point_on_display_normalized[0], 0.4, places=5)

    def test_on_gaze_point_callback(self):
        gp = tobii_4c_osc.tobii_gaze_point_t()
        gp.validity = tobii_4c_osc.TobiiValidity.TOBII_VALIDITY_VALID
        gp.position_xy[0] = 0.3
        gp.position_xy[1] = 0.7

        gp_ptr = ctypes.pointer(gp)
        tobii_4c_osc.on_gaze_point(gp_ptr, None)

        self.assertIsNotNone(tobii_4c_osc.state.last_gaze_data)
        self.assertAlmostEqual(tobii_4c_osc.state.features[6].current_val, 0.3, places=5)
        self.assertAlmostEqual(tobii_4c_osc.state.features[7].current_val, 0.7, places=5)
        tobii_4c_osc.state.client.send_message.assert_any_call("/gaze_x", tobii_4c_osc.state.features[6].current_val)
        tobii_4c_osc.state.client.send_message.assert_any_call("/gaze_y", tobii_4c_osc.state.features[7].current_val)

    def test_on_gaze_data_callback(self):
        gd = tobii_4c_osc.tobii_gaze_data_t()
        gd.left_gaze_point_validity = tobii_4c_osc.TobiiValidity.TOBII_VALIDITY_VALID
        gd.left_gaze_point_on_display_normalized[0] = 0.2
        gd.left_gaze_point_on_display_normalized[1] = 0.4
        gd.right_gaze_point_validity = tobii_4c_osc.TobiiValidity.TOBII_VALIDITY_VALID
        gd.right_gaze_point_on_display_normalized[0] = 0.4
        gd.right_gaze_point_on_display_normalized[1] = 0.6
        gd.left_pupil_validity = tobii_4c_osc.TobiiValidity.TOBII_VALIDITY_VALID
        gd.left_pupil_diameter_mm = 3.5
        gd.right_pupil_validity = tobii_4c_osc.TobiiValidity.TOBII_VALIDITY_VALID
        gd.right_pupil_diameter_mm = 3.7

        gd_ptr = ctypes.pointer(gd)
        tobii_4c_osc.on_gaze_data(gd_ptr, None)

        self.assertIsNotNone(tobii_4c_osc.state.last_gaze_data)
        self.assertAlmostEqual(tobii_4c_osc.state.features[6].current_val, 0.3, places=5) # Average X
        self.assertAlmostEqual(tobii_4c_osc.state.features[7].current_val, 0.5, places=5) # Average Y
        self.assertAlmostEqual(tobii_4c_osc.state.features[8].current_val, 0.2, places=5) # Left X
        self.assertAlmostEqual(tobii_4c_osc.state.features[10].current_val, 0.4, places=5) # Right X
        self.assertAlmostEqual(tobii_4c_osc.state.features[12].current_val, 3.5, places=5) # Left Pupil
        self.assertAlmostEqual(tobii_4c_osc.state.features[13].current_val, 3.7, places=5) # Right Pupil

    def test_on_head_pose_callback(self):
        hp = tobii_4c_osc.tobii_head_pose_t()
        hp.position_validity = tobii_4c_osc.TobiiValidity.TOBII_VALIDITY_VALID
        hp.position_xyz[0] = 10.0
        hp.position_xyz[1] = -20.0
        hp.position_xyz[2] = 500.0
        hp.rotation_validity = tobii_4c_osc.TobiiValidity.TOBII_VALIDITY_VALID
        hp.rotation_xyz[0] = math.radians(15.0)
        hp.rotation_xyz[1] = math.radians(-5.0)
        hp.rotation_xyz[2] = math.radians(0.0)

        hp_ptr = ctypes.pointer(hp)
        tobii_4c_osc.on_head_pose(hp_ptr, None)

        self.assertAlmostEqual(tobii_4c_osc.state.features[0].current_val, 10.0, places=5) # Pose X
        self.assertAlmostEqual(tobii_4c_osc.state.features[1].current_val, -20.0, places=5) # Pose Y
        self.assertAlmostEqual(tobii_4c_osc.state.features[2].current_val, 500.0, places=5) # Pose Z
        self.assertAlmostEqual(tobii_4c_osc.state.features[3].current_val, 15.0, places=4) # Pitch
        self.assertAlmostEqual(tobii_4c_osc.state.features[4].current_val, -5.0, places=4) # Yaw

    def test_load_tobii_stream_engine_returns_none_when_missing(self):
        with patch('ctypes.CDLL', side_effect=OSError("DLL not found")):
            lib = tobii_4c_osc.load_tobii_stream_engine()
            self.assertIsNone(lib)

    def test_osc_port_default(self):
        self.assertEqual(tobii_4c_osc.OSC_PORT, 9002)

    def test_is_admin(self):
        # Non-win32 should return True
        with patch('sys.platform', 'linux'):
            self.assertTrue(tobii_4c_osc.is_admin())

        # win32 admin check test
        with patch('sys.platform', 'win32'):
            mock_shell32 = MagicMock()
            mock_shell32.IsUserAnAdmin.return_value = 1
            with patch.dict('sys.modules', {'ctypes': MagicMock(windll=MagicMock(shell32=mock_shell32))}):
                self.assertTrue(tobii_4c_osc.is_admin())

            mock_shell32.IsUserAnAdmin.return_value = 0
            with patch.dict('sys.modules', {'ctypes': MagicMock(windll=MagicMock(shell32=mock_shell32))}):
                self.assertFalse(tobii_4c_osc.is_admin())

    def test_window_minimization(self):
        with patch('sys.platform', 'win32'):
            mock_user32 = MagicMock()
            mock_kernel32 = MagicMock()
            mock_kernel32.GetConsoleWindow.return_value = 12345
            mock_user32.FindWindowW.return_value = 67890

            with patch.dict('sys.modules', {'ctypes': MagicMock(windll=MagicMock(user32=mock_user32, kernel32=mock_kernel32))}):
                tobii_4c_osc.minimize_console_window()
                mock_user32.ShowWindow.assert_called_with(12345, 6)

                tobii_4c_osc.minimize_gui_window('Tobii 4C OSC (Stream Engine)')
                mock_user32.FindWindowW.assert_called_with(None, 'Tobii 4C OSC (Stream Engine)')
                mock_user32.ShowWindow.assert_called_with(67890, 6)

    def test_tcp_server_toggle_mouse(self):
        tobii_4c_osc.state.move_mouse = True
        tobii_4c_osc.state.running = True

        test_port = 9999
        tobii_4c_osc.start_tcp_server(host="127.0.0.1", port=test_port)
        time.sleep(0.1)

        try:
            with socket.create_connection(("127.0.0.1", test_port), timeout=2.0) as s:
                s.sendall(b"toggle\n")
                resp = s.recv(1024)
                self.assertIn(b"Mouse control:", resp)

            self.assertFalse(tobii_4c_osc.state.move_mouse)
        finally:
            tobii_4c_osc.state.running = False

if __name__ == '__main__':
    unittest.main()
