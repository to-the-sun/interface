import unittest
import os
import json
import tempfile
from unittest.mock import patch

from MouseSmoother.mouse_smoother import (
    compute_smoothing,
    MouseSmootherEngine,
    load_config,
    save_config,
    DEFAULT_CONFIG
)

class TestMouseSmoother(unittest.TestCase):

    def test_compute_smoothing_threshold(self):
        # Jump below or equal to min_jump should result in 0 smoothing
        min_jump = 10.0
        max_jump = 100.0
        max_smoothing = 0.8
        curve_factor = 0.0

        self.assertEqual(compute_smoothing(0.0, min_jump, max_jump, max_smoothing, curve_factor), 0.0)
        self.assertEqual(compute_smoothing(5.0, min_jump, max_jump, max_smoothing, curve_factor), 0.0)
        self.assertEqual(compute_smoothing(10.0, min_jump, max_jump, max_smoothing, curve_factor), 0.0)

    def test_compute_smoothing_linear(self):
        min_jump = 10.0
        max_jump = 110.0  # Range of 100
        max_smoothing = 0.8
        curve_factor = 0.0

        # At mid point jump=60 (norm = 0.5), smoothing should be 0.5 * 0.8 = 0.4
        sm_mid = compute_smoothing(60.0, min_jump, max_jump, max_smoothing, curve_factor)
        self.assertAlmostEqual(sm_mid, 0.4, places=5)

        # At max point jump=110 (norm = 1.0), smoothing should be max_smoothing = 0.8
        sm_max = compute_smoothing(110.0, min_jump, max_jump, max_smoothing, curve_factor)
        self.assertAlmostEqual(sm_max, 0.8, places=5)

        # Beyond max point jump=200, smoothing should clamp at max_smoothing = 0.8
        sm_over = compute_smoothing(200.0, min_jump, max_jump, max_smoothing, curve_factor)
        self.assertAlmostEqual(sm_over, 0.8, places=5)

    def test_compute_smoothing_exponential(self):
        min_jump = 0.0
        max_jump = 100.0
        max_smoothing = 0.8
        curve_factor = 2.0  # Exponential: norm^(1+2) = norm^3

        # At norm = 0.5 (jump = 50), factor = 0.5^3 = 0.125
        # Expected smoothing = 0.125 * 0.8 = 0.1
        sm = compute_smoothing(50.0, min_jump, max_jump, max_smoothing, curve_factor)
        self.assertAlmostEqual(sm, 0.1, places=5)

    def test_compute_smoothing_logarithmic(self):
        min_jump = 0.0
        max_jump = 100.0
        max_smoothing = 0.8
        curve_factor = -2.0  # Logarithmic: 1 - (1 - norm)^(1+2) = 1 - (1 - norm)^3

        # At norm = 0.5 (jump = 50), factor = 1 - 0.5^3 = 0.875
        # Expected smoothing = 0.875 * 0.8 = 0.7
        sm = compute_smoothing(50.0, min_jump, max_jump, max_smoothing, curve_factor)
        self.assertAlmostEqual(sm, 0.7, places=5)

    def test_config_load_save(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_config_path = os.path.join(tmpdir, "test_config.json")

            with patch("MouseSmoother.mouse_smoother.get_config_path", return_value=test_config_path):
                # Load default when file missing
                cfg = load_config()
                self.assertEqual(cfg["min_jump"], DEFAULT_CONFIG["min_jump"])

                # Save modified config
                cfg["min_jump"] = 15.5
                cfg["curve_factor"] = 1.5
                save_config(cfg)

                # Reload and verify
                reloaded = load_config()
                self.assertEqual(reloaded["min_jump"], 15.5)
                self.assertEqual(reloaded["curve_factor"], 1.5)

    def test_engine_initialization_and_start_stop(self):
        config = {
            "min_jump": 5.0,
            "max_jump": 100.0,
            "max_smoothing": 0.8,
            "curve_factor": 0.0,
            "enabled": False
        }
        engine = MouseSmootherEngine(config)
        self.assertFalse(engine.running)

        engine.start()
        self.assertTrue(engine.running)

        engine.stop()
        self.assertFalse(engine.running)

if __name__ == "__main__":
    unittest.main()
