import sys
import unittest
from unittest.mock import MagicMock

try:
    import sounddevice
except Exception:
    sys.modules['sounddevice'] = MagicMock()

import numpy as np
import math
from audio_compressor import AudioCompressor

class TestAudioCompressor(unittest.TestCase):
    def setUp(self):
        self.compressor = AudioCompressor(sample_rate=44100)
        self.compressor.threshold_db = -20.0
        self.compressor.ratio = 4.0
        self.compressor.attack_ms = 1.0
        self.compressor.release_ms = 10.0
        self.compressor.makeup_gain_db = 0.0
        self.compressor.enabled = True

    def test_pass_through_silence(self):
        silence = np.zeros((512, 1), dtype=np.float32)
        out = self.compressor.process(silence)
        np.testing.assert_array_equal(out, silence)
        self.assertLess(self.compressor.current_in_db, -90.0)
        self.assertEqual(self.compressor.current_gr_db, 0.0)

    def test_signal_below_threshold_uncompressed(self):
        # -30 dB signal (below -20 dB threshold)
        amp = 10.0 ** (-30.0 / 20.0)
        signal = np.full((512, 1), amp, dtype=np.float32)
        out = self.compressor.process(signal)

        # Output should equal input because makeup gain is 0 and no compression occurs
        np.testing.assert_allclose(out, signal, rtol=1e-4)
        self.assertEqual(self.compressor.current_gr_db, 0.0)

    def test_signal_above_threshold_compressed(self):
        # 0 dB signal (above -20 dB threshold)
        amp = 1.0
        signal = np.full((512, 1), amp, dtype=np.float32)

        # Process multiple blocks to allow envelope follower to stabilize
        for _ in range(20):
            out = self.compressor.process(signal)

        # Expect Gain Reduction around (0 - (-20)) * (1 - 1/4) = 20 * 0.75 = 15 dB
        self.assertGreater(self.compressor.current_gr_db, 10.0)
        self.assertLessEqual(self.compressor.current_gr_db, 15.0)

        # Compressed signal level should be lower than input signal level
        out_peak = float(np.max(np.abs(out)))
        self.assertLess(out_peak, amp)

    def test_bypassed_compressor(self):
        self.compressor.enabled = False
        amp = 1.0
        signal = np.full((512, 1), amp, dtype=np.float32)

        out = self.compressor.process(signal)

        # Gain reduction should be 0 when bypassed
        self.assertEqual(self.compressor.current_gr_db, 0.0)

    def test_makeup_gain(self):
        self.compressor.threshold_db = 0.0  # no compression
        self.compressor.makeup_gain_db = 6.0 # +6 dB (~2x amplitude)

        amp = 0.2
        signal = np.full((512, 1), amp, dtype=np.float32)
        out = self.compressor.process(signal)

        expected_amp = amp * (10.0 ** (6.0 / 20.0))
        np.testing.assert_allclose(out, np.full((512, 1), expected_amp, dtype=np.float32), rtol=1e-3)

    def test_peak_limiter(self):
        self.compressor.makeup_gain_db = 30.0 # Extreme gain to force potential clipping
        amp = 0.5
        signal = np.full((512, 1), amp, dtype=np.float32)
        out = self.compressor.process(signal)

        # Verify clipping ceiling of 0.99
        self.assertLessEqual(float(np.max(out)), 0.990001)
        self.assertGreaterEqual(float(np.min(out)), -0.990001)

if __name__ == "__main__":
    unittest.main()
