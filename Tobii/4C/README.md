# Tobii 4C OSC Streamer (Tobii Stream Engine API)

This program streams gaze and head pose data from a Tobii 4C eye tracker to OSC, mirroring the functionality and UI of the `Google/MediaPipe/mediapipe_osc.py` script.

It connects to the **Tobii Stream Engine API** using Python's `ctypes`, removing the requirement for `tobii-research` (Tobii Pro SDK) or special Pro Upgrade licensing.

## Requirements

1.  **Python 3.8+**: Compatible with Python 3.8, 3.9, 3.10, 3.11, 3.12, and newer versions.
2.  **Tobii Core Software / Eye Tracking Service**: Tobii Core software or Eye Tracking Service installed on Windows (provides `tobii_stream_engine.dll`).
3.  **Python Packages**:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the script from the directory:

```bash
python tobii_4c_osc.py
```

- **Port**: Streams to `127.0.0.1:9001` by default.
- **Interactions**:
    - Use the checkboxes in the sidebar to toggle specific OSC addresses on or off.
    - Press **'n'** to cycle through connected Tobii trackers.
    - Press **ESC** to exit.

## OSC Message Mapping

The script streams to the following addresses (standardized to snake_case):

### Head Pose
- `/pose_x`, `/pose_y`, `/pose_z`: Head position in mm.
- `/pose_pitch`, `/pose_yaw`, `/pose_roll`: Head rotation in degrees.

### Gaze
- `/gaze_x`, `/gaze_y`: Average horizontal and vertical gaze (0.0 to 1.0).
- `/left/gaze_x`, `/left/gaze_y`: Left eye gaze.
- `/right/gaze_x`, `/right/gaze_y`: Right eye gaze.
- `/left/pupil_diameter`, `/right/pupil_diameter`: Pupil diameter in mm.

## Troubleshooting

- **"Could not load tobii_stream_engine.dll"**:
    - Ensure Tobii Core Software or Eye Tracking Service is installed.
    - Verify `tobii_stream_engine.dll` is available in system PATH or Tobii installation folders.
- **"No Tobii eye trackers found via Tobii Stream Engine API"**:
    - Ensure Tobii Core software / Tobii Eye Tracking Service is running.
    - Ensure the Tobii 4C tracker is plugged in and calibrated.
