# Tobii PCEye 5 to OSC Streamer

This tool streams real-time gaze data from a **Tobii Dynavox PCEye 5** (the assistive/accessibility model) or **Tobii Pro** devices to Open Sound Control (OSC).

## Requirements

1.  **Python 3.x**
2.  **Tobii Runtime/Service**: Ensure the Tobii software is installed and your device is calibrated.
3.  **Python Packages**:
    ```bash
    pip install tobii-research python-osc
    ```

## Usage

Run the script from the command line:

```bash
python tobii_osc.py --ip 127.0.0.1 --port 6731
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

*   **Device Compatibility**: This script uses the `tobii_research` (Tobii Pro) SDK.
    *   **PCEye 5 (Dynavox)**: Supported (includes Pro/Analytical license).
    *   **Tobii Pro Trackers (Fusion, Spark, etc.)**: Supported.
    *   **Tobii Eye Tracker 5 (Consumer/Gaming)**: **Not natively supported** by this SDK. Gaming trackers require the "Stream Engine" API or a separate "Pro Upgrade" license from Tobii.
*   **"No Tobii eye trackers found"**: Ensure the eye tracker is plugged in and recognized by the "Tobii Experience" or "TD Control" software.
*   **Permissions**: On some systems, you may need to run the terminal as Administrator/Sudo to access the Tobii SDK.
