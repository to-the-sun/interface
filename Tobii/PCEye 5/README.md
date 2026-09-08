# Tobii PCEye 5 to OSC Streamer & Mouse Control

This tool streams real-time gaze data from a **Tobii Dynavox PCEye 5** (or Tobii Pro devices) to Open Sound Control (OSC) and moves the mouse cursor onscreen based on gaze data by default.

---

## Complete Out-of-the-Box Setup Instructions

Follow these step-by-step instructions to set up a brand new **Tobii PCEye 5** from unboxing to running this script.

### Step 1: Unboxing & Physical Setup
1. **Unpack the PCEye 5**: Inside the box, you will find the PCEye 5 tracker bar, magnetic mounting plates, alcohol wipe, and optional USB-A adapters.
2. **Clean the Mounting Area**: Use the provided alcohol wipe to clean the lower bezel/frame of your display monitor (directly beneath the screen).
3. **Attach the Magnetic Mount**:
   - Peel off the protective backing from the adhesive strip on the metal mounting plate.
   - Attach the plate firmly centered to the bottom bezel of your monitor. Press and hold for 30 seconds.
4. **Mount the PCEye 5**: Snap the PCEye 5 bar onto the magnetic mount so that the lenses face you and point slightly upward towards your eyes.
5. **Connect to Computer**: Plug the USB cable into a USB-C port (or use the provided USB-C to USB-A adapter to connect to a USB 3.0 port on your PC).

---

### Step 2: Install Tobii Dynavox Software & Drivers
1. **Download TD Control / PCEye Drivers**:
   - Go to the official Tobii Dynavox support page: [https://www.tobiidynavox.com/pages/pceye-support](https://www.tobiidynavox.com/pages/pceye-support)
   - Download and run the **TD Control** installer (or **PCEye Software / Tobii Gaze Interaction Software** installer).
2. **Complete Software Installation**:
   - Follow the wizard on-screen prompts to install the drivers, Tobii Service/Runtime, and TD Control.
   - Reboot your computer if prompted by the installer.

---

### Step 3: Device Calibration
1. **Launch TD Control / Tobii Eye Tracking Settings**:
   - Open **TD Control** from your Start menu or system tray.
2. **Display Setup**:
   - Select your screen size and confirm the physical mounting position relative to your display screen.
3. **Calibrate**:
   - Click **Calibrate** or start a new calibration profile.
   - Position yourself 50–70 cm (20–28 inches) away from the monitor.
   - Ensure the track status indicator shows both of your eyes centered in the green zone.
   - Follow the target dots across the screen with your eyes until calibration completes.
   - Save your calibration profile.

---

### Step 4: Install Python Dependencies
1. Ensure **Python 3.8 or higher** (Python 3.10 recommended) is installed on your Windows PC.
2. Open Command Prompt or PowerShell in the `Tobii/PCEye 5/` directory and run:
   ```cmd
   pip install -r requirements.txt
   ```
   *(Or double-click `run_tobii.bat`, which will automatically check and install requirements for you).*

---

### Step 5: Run the Script
Double-click `run_tobii.bat` or run via command prompt:

```cmd
python tobii_osc.py
```

- **Default Behavior**:
  - Automatically connects to the PCEye 5.
  - **Moves the mouse cursor onscreen** in real-time to follow your eye gaze.
  - **Streams OSC data** to `127.0.0.1:6731`.

---

## Command Line Options

| Argument | Description | Default |
| --- | --- | --- |
| `--ip` | Destination IP address for OSC messages | `127.0.0.1` |
| `--port` | Destination UDP port for OSC messages | `6731` |
| `--no-mouse` | Disable moving screen mouse cursor with gaze data | Mouse movement enabled |

### Examples:
- **Run with mouse control disabled (OSC streaming only)**:
  ```cmd
  python tobii_osc.py --no-mouse
  ```
- **Send OSC to custom IP and port**:
  ```cmd
  python tobii_osc.py --ip 192.168.1.100 --port 9001
  ```

---

## OSC Message Mapping

The script streams data to the following addresses:

### Primary Gaze (Average of both eyes)
* `/Tobii/gaze_x`: Horizontal gaze (0.0 = Left, 1.0 = Right)
* `/Tobii/gaze_y`: Vertical gaze (0.0 = Top, 1.0 = Bottom)

### OpenFace 3.0 Compatibility
To maintain compatibility with OpenFace 3.0 (Lite) receivers:
* `/OpenFace/gaze_left_right`: Approximate degrees (-30 to 30)
* `/OpenFace/gaze_up_down`: Approximate degrees (-30 to 30)

### Per-Eye Data
* `/Tobii/left/gaze_x`, `/Tobii/left/gaze_y`: Normalized coordinates for left eye.
* `/Tobii/right/gaze_x`, `/Tobii/right/gaze_y`: Normalized coordinates for right eye.
* `/Tobii/left/pupil_diameter`: Pupil diameter in mm.
* `/Tobii/right/pupil_diameter`: Pupil diameter in mm.

---

## Troubleshooting

1. **"No Tobii eye trackers found!"**:
   - Ensure the Tobii Service / TD Control is running in the system tray.
   - Unplug and reconnect the USB cable.
   - Verify device appears in Windows Device Manager under "Tobii Eye Tracker" or "Universal Serial Bus devices".
2. **Mouse pointer jumps or isn't accurate**:
   - Re-run the calibration in TD Control under well-lit indoor conditions.
   - Avoid direct sunlight or heavy infrared light hitting the tracker.
3. **Permissions / Elevation**:
   - If attempting to interact with elevated/administrator windows, launch Command Prompt as Administrator before running `python tobii_osc.py`.
