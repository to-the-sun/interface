# Tobii 4C OSC Streamer

This program streams gaze and head pose data from a Tobii 4C eye tracker to OSC, mirroring the functionality and UI of the `Google/MediaPipe/mediapipe_osc.py` script.

## Requirements

1.  **Python 3.10**: The `tobii-research` library is currently most compatible with Python 3.10. If you encounter issues installing it on other versions, please use Python 3.10.
2.  **Tobii Pro SDK License**: The Tobii 4C is a consumer device. Accessing it via the `tobii-research` (Tobii Pro SDK) library requires a **Pro Upgrade** license from Tobii.
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

- **"Could not find a version that satisfies the requirement tobii-research"**: This usually means your Python version is not supported by the available wheels on PyPI. Ensure you are using **Python 3.10**.
- **"No Tobii eye trackers found"**:
    - Ensure the Tobii Core/Eye Tracking software is running.
    - Ensure the device is calibrated and active.
    - Check if you have the required license for the Pro SDK.
