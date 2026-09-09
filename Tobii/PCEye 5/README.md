# Tobii PCEye 5 to OSC Streamer

This tool streams real-time gaze data from a **Tobii Dynavox PCEye 5** (the assistive/accessibility model) or **Tobii Pro** devices to Open Sound Control (OSC).

## Requirements

1.  **Python 3.10 (64-bit)**: The `tobii-research` (Tobii Pro SDK) library only provides pre-compiled wheels on PyPI for Python 3.10 and Python 3.8. Python 3.11, 3.12, and newer versions are not supported by Tobii's wheels.
2.  **Tobii Runtime/Service**: Ensure the Tobii software (TD Control or Tobii Pro Eye Tracker Manager) is installed and your device is calibrated.
3.  **Automatic Environment**: Running `run_tobii.bat` will automatically set up a local Python 3.10 environment (`py310_env`), download portable Python 3.10 if missing from your system, and install all required dependencies automatically.

## Usage

Simply double-click or run the batch script:
```cmd
run_tobii.bat
```

Or run directly with Python 3.10:
```bash
py -3.10 tobii_osc.py --ip 127.0.0.1 --port 6731
```

## OSC Message Mapping

The script streams data to the following addresses:

### Primary Gaze (Average of both eyes)
*   `/Tobii/gaze_x`: Horizontal gaze (0.0 = Left, 1.0 = Right)
*   `/Tobii/gaze_y`: Vertical gaze (0.0 = Top, 1.0 = Bottom)

### OpenFace 3.0 Compatibility
To maintain compatibility with OpenFace 3.0 (Lite) receivers, the script also sends:
*   `/OpenFace/gaze_left_right`: Approximate degrees (-30 to 30)
*   `/OpenFace/gaze_up_down`: Approximate degrees (-30 to 30)

### Per-Eye Data
*   `/Tobii/left/gaze_x`, `/Tobii/left/gaze_y`: Normalized coordinates for left eye.
*   `/Tobii/right/gaze_x`, `/Tobii/right/gaze_y`: Normalized coordinates for right eye.
*   `/Tobii/left/pupil_diameter`: Pupil diameter in mm.
*   `/Tobii/right/pupil_diameter`: Pupil diameter in mm.

## Troubleshooting

*   **"Could not find a version that satisfies the requirement tobii-research"**:
    *   This error occurs when trying to install `tobii-research` on an unsupported Python version (such as Python 3.11, 3.12, 3.13, or a 32-bit Python installation).
    *   **Solution**: Simply run `run_tobii.bat`. It will automatically download a portable Python 3.10 package into a local `py310_env` directory and install `tobii-research` into it automatically.
*   **Device Compatibility**: This script uses the `tobii_research` (Tobii Pro SDK) SDK.
    *   **PCEye 5 (Dynavox)**: Supported (includes Pro/Analytical license).
    *   **Tobii Pro Trackers (Fusion, Spark, etc.)**: Supported.
    *   **Tobii Eye Tracker 5 (Consumer/Gaming)**: **Not natively supported** by this SDK. Gaming trackers require the "Stream Engine" API or a separate "Pro Upgrade" license from Tobii.
*   **"No Tobii eye trackers found"**: Ensure the eye tracker is plugged in and recognized by the "Tobii Experience" or "TD Control" software.
*   **Permissions**: On some systems, you may need to run the terminal as Administrator/Sudo to access the Tobii SDK.
