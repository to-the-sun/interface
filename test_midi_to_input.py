import unittest
from unittest.mock import MagicMock, patch
import time
import mido

# Import classes to test
from midi_to_input import MidiInputController, MouseMonitor, Button, Key

class TestMidiInputController(unittest.TestCase):
    def setUp(self):
        # Create mock mouse, keyboard, and frozen check
        self.mock_mouse = MagicMock()
        self.mock_keyboard = MagicMock()
        self.is_frozen = False
        self.mock_is_frozen_func = lambda: self.is_frozen

        # Instantiate MIDI Input Controller
        self.controller = MidiInputController(
            self.mock_mouse,
            self.mock_keyboard,
            self.mock_is_frozen_func
        )

    def test_left_click_on_pitch_127(self):
        # When a MIDI NOTE ON is received for pitch 127, generate a left click
        msg = mido.Message('note_on', note=127, velocity=64)
        self.controller.handle_midi_message(msg)
        self.mock_mouse.click.assert_called_once_with(Button.left, 1)

    def test_right_click_on_pitch_126(self):
        # When a MIDI NOTE ON is received for pitch 126, generate a right click
        msg = mido.Message('note_on', note=126, velocity=64)
        self.controller.handle_midi_message(msg)
        self.mock_mouse.click.assert_called_once_with(Button.right, 1)

    def test_double_click_on_pitch_125(self):
        # When a MIDI NOTE ON is received for pitch 125, generate a double click
        msg = mido.Message('note_on', note=125, velocity=64)
        self.controller.handle_midi_message(msg)
        self.mock_mouse.click.assert_called_once_with(Button.left, 2)

    def test_drag_start_and_end_on_pitch_124(self):
        # When a MIDI NOTE ON is received for pitch 124, initiate a drag
        msg_on = mido.Message('note_on', note=124, velocity=64)
        self.controller.handle_midi_message(msg_on)
        self.mock_mouse.press.assert_called_once_with(Button.left)
        self.assertTrue(self.controller.is_dragging)

        # When a MIDI note off is received for pitch 124, conclude the drag
        msg_off = mido.Message('note_off', note=124, velocity=0)
        self.controller.handle_midi_message(msg_off)
        self.mock_mouse.release.assert_called_once_with(Button.left)
        self.assertFalse(self.controller.is_dragging)

    def test_f4_keypress_and_mode_paused_on_pitch_123(self):
        # When a MIDI NOTE ON is received for pitch 123, simulate F4 keypress and change mode to paused
        msg = mido.Message('note_on', note=123, velocity=64)
        self.controller.handle_midi_message(msg)
        self.mock_keyboard.press.assert_called_once_with(Key.f4)
        self.mock_keyboard.release.assert_called_once_with(Key.f4)
        self.assertEqual(self.controller.mode, "paused")

    def test_f4_keypress_and_mode_frozen_on_pitch_122(self):
        # When a MIDI NOTE ON is received for pitch 122, simulate F4 keypress and change mode to frozen
        msg = mido.Message('note_on', note=122, velocity=64)
        self.controller.handle_midi_message(msg)
        self.mock_keyboard.press.assert_called_once_with(Key.f4)
        self.mock_keyboard.release.assert_called_once_with(Key.f4)
        self.assertEqual(self.controller.mode, "frozen")

    def test_mouse_frozen_disables_all_except_allowed_exceptions(self):
        # If the mouse is frozen in place, all functions should be disabled...
        self.is_frozen = True
        self.controller.mode = "active"

        # Try to do a left click on pitch 127
        msg = mido.Message('note_on', note=127, velocity=64)
        self.controller.handle_midi_message(msg)
        self.mock_mouse.click.assert_not_called()

        # Try to change mode on pitch 122/123 when mode is 'active' and mouse is frozen
        msg_123 = mido.Message('note_on', note=123, velocity=64)
        self.controller.handle_midi_message(msg_123)
        self.mock_keyboard.press.assert_not_called()

    def test_mouse_frozen_exception_pitch_123_paused_mode(self):
        # exception: receiving a NOTE ON for pitch 123 if in `paused` mode
        self.is_frozen = True
        self.controller.mode = "paused"

        msg = mido.Message('note_on', note=123, velocity=64)
        self.controller.handle_midi_message(msg)
        self.mock_keyboard.press.assert_called_once_with(Key.f4)

    def test_mouse_frozen_exception_pitch_122_paused_and_frozen_mode(self):
        # exception: receiving a NOTE ON for pitch 122 if in `paused` or `frozen` mode
        self.is_frozen = True

        # Test paused mode
        self.controller.mode = "paused"
        msg = mido.Message('note_on', note=122, velocity=64)
        self.controller.handle_midi_message(msg)
        self.mock_keyboard.press.assert_called_once_with(Key.f4)

        self.mock_keyboard.reset_mock()

        # Test frozen mode
        self.controller.mode = "frozen"
        self.controller.handle_midi_message(msg)
        self.mock_keyboard.press.assert_called_once_with(Key.f4)

    def test_note_on_with_velocity_zero_acts_as_note_off(self):
        # A note_on message with velocity 0 is standard MIDI for note_off
        self.controller.is_dragging = True
        msg = mido.Message('note_on', note=124, velocity=0)
        self.controller.handle_midi_message(msg)
        self.mock_mouse.release.assert_called_once_with(Button.left)
        self.assertFalse(self.controller.is_dragging)


class TestMouseMonitor(unittest.TestCase):
    def test_mouse_monitor_tracks_freeze_status(self):
        mock_mouse = MagicMock()
        mock_mouse.position = (100, 100)

        monitor = MouseMonitor(mock_mouse, interval=0.01, frozen_threshold=0.05)
        self.assertFalse(monitor.is_frozen())

        # Fast-forward time to simulate frozen status
        with patch('time.time', return_value=time.time() + 1.0):
            self.assertTrue(monitor.is_frozen())


if __name__ == "__main__":
    unittest.main()
