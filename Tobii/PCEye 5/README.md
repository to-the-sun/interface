# Tobii PCEye 5 to OSC Streamer & Mouse Control

This tool streams real-time gaze data from a **Tobii Dynavox PCEye 5** (or **Tobii Pro** devices) to Open Sound Control (OSC) and moves the onscreen mouse cursor based on gaze position by default.

---

## Brand New PCEye 5 Out-of-the-Box Setup Guide

Follow these exact step-by-step instructions to set up your brand new Tobii PCEye 5 from unboxing to streaming and mouse control.

### Step 1: Hardware Setup & Mounting

1. **Unbox the PCEye 5**: Remove the PCEye 5 tracker bar, USB extension cable (if included), and magnetic mounting plates from the box.
2. **Mount the Bracket**:
   - Clean the bottom bezel of your computer monitor or laptop screen (directly below the display area).
   - Peel off the protective adhesive strip from the magnetic mounting plate.
   - Firmly press the mounting plate onto the center of the bottom screen bezel for at least 30 seconds.
3. **Attach the Device**:
   - Snap the PCEye 5 bar onto the magnetic mounting bracket. Ensure the dual infrared cameras and illuminators face toward your seating position.
4. **Connect USB**:
   - Plug the USB-A cable directly into a powered USB 2.0 or USB 3.0 port on your computer. Avoid unpowered USB hubs to ensure sufficient power supply.

---

### Step 2: Tobii Software & Driver Installation

1. **Download TD Control**:
   - Visit the official Tobii Dynavox support website: [https://www.tobiidynavox.com/](https://www.tobiidynavox.com/)
   - Navigate to **Support & Downloads** and download **TD Control** (or **PCEye Software / Tobii Eye Tracking**).
2. **Install the Software**:
   - Run the downloaded installer (`TDControl_Setup.exe` or equivalent).
   - Follow the onscreen prompts to complete the installation. This automatically installs required Windows drivers and the **Tobii Service / Runtime**.
3. **Verify Device Recognition**:
   - Once installed, check that the status light on the PCEye 5 is illuminated.

---

### Step 3: Display Configuration & Calibration

1. **Configure Screen Display**:
   - Open **TD Control** or **Tobii PCEye Settings**.
   - Select **Display Setup** and choose the screen/monitor on which the PCEye 5 is mounted.
2. **Perform Eye Calibration**:
   - Click **Calibrate** in the software.
   - Sit in a comfortable position about 45–75 cm (18–30 inches) away from the monitor.
   - Ensure your eyes are positioned within the guide box shown on screen.
   - Follow the on-screen calibration target as it moves across various calibration points on the display.
   - Save the calibration profile when prompted.

---

### Step 4: Running the OSC Streamer & Mouse Control

#### Quick Start (Automated Environment)
Simply double-click or run the batch script on Windows:
```cmd
run_tobii.bat
```
`run_tobii.bat` automatically:
- Checks for or downloads an isolated portable **Python 3.10 64-bit** environment (`py310_env`).
- Installs all required dependencies (`tobii-research`, `python-osc`, `pynput`).
- Launches `tobii_osc.py` with default mouse cursor movement and OSC streaming.

#### Manual Execution
If running manually with Python 3.10:
```bash
# 1. Install required dependencies
py -3.10 -m pip install -r requirements.txt

# 2. Run script with default options (OSC streaming + Onscreen Mouse Control)
py -3.10 tobii_osc.py
```

---

## Features & Options

### Onscreen Mouse Cursor Control
* **Enabled by Default**: The script converts normalized gaze coordinates into screen pixels and moves the Windows/system mouse cursor to where you are looking.
* **Disable Mouse Control**: If you only want to stream OSC data without moving the mouse cursor, pass the `--no-mouse` flag:
  ```bash
  py -3.10 tobii_osc.py --no-mouse
  ```
  *(Or edit `run_tobii.bat` to append `--no-mouse` to the command line call).*

### Command-Line Arguments
| Option | Default | Description |
| :--- | :--- | :--- |
| `--ip` | `127.0.0.1` | OSC Destination IP address |
| `--port` | `6731` | OSC Destination UDP port |
| `--no-mouse` | `False` | Disable moving mouse cursor onscreen using gaze data |

---

## OSC Message Mapping

The script streams data to the following OSC addresses:

### Primary Gaze (Average of both eyes)
* `/Tobii/gaze_x`: Horizontal gaze position (0.0 = Left edge, 1.0 = Right edge)
* `/Tobii/gaze_y`: Vertical gaze position (0.0 = Top edge, 1.0 = Bottom edge)

### OpenFace 3.0 / OpenFace Lite Compatibility
To maintain compatibility with OpenFace receivers, the script sends:
* `/OpenFace/gaze_left_right`: Approximate gaze angle in degrees (-30 to 30)
* `/OpenFace/gaze_up_down`: Approximate gaze angle in degrees (-30 to 30)

### Per-Eye Data
* `/Tobii/left/gaze_x`, `/Tobii/left/gaze_y`: Normalized gaze coordinates for left eye.
* `/Tobii/right/gaze_x`, `/Tobii/right/gaze_y`: Normalized gaze coordinates for right eye.
* `/Tobii/left/pupil_diameter`: Pupil diameter in mm (if available).
* `/Tobii/right/pupil_diameter`: Pupil diameter in mm (if available).

---

## Troubleshooting

* **"No Tobii eye trackers found"**:
  1. Ensure the PCEye 5 USB cable is plugged directly into your PC.
  2. Verify that **TD Control** or **Tobii Service** is running in the system tray.
  3. Ensure the eye tracker is calibrated in TD Control before launching the script.
* **"Could not find a version that satisfies the requirement tobii-research"**:
  * The `tobii-research` SDK only provides pre-compiled Python wheels for **Python 3.10** (and 3.8) 64-bit. Python 3.11, 3.12, 3.13+ are NOT supported by Tobii's PyPI package.
  * **Solution**: Run `run_tobii.bat`. It will create an isolated portable Python 3.10 environment automatically.
* **Consumer Tobii Eye Tracker 5 vs PCEye 5**:
  * **PCEye 5 (Dynavox)**: Fully supported out of the box (includes Tobii Pro license).
  * **Tobii Eye Tracker 5 (Consumer/Gaming)**: Not natively supported by the Tobii Pro SDK unless unlocked with a Pro Upgrade license.
* **Device Detected but `Frames: 0 (0.0 fps)` / No Mouse Cursor Movement**:
  * **Uncalibrated Device**: The Tobii PCEye 5 will not emit gaze stream callbacks until **Display Setup** and **Calibration** are completed in TD Control. Launch TD Control and save a calibration profile.
  * **Stalled Tobii Service**: Open Windows Task Manager / Services (`services.msc`), restart `Tobii Service` or `TD Control`, then re-run `run_tobii.bat`.
  * **USB Port Power**: Ensure the PCEye 5 USB cable is plugged directly into a high-power USB 3.0 port on your PC's motherboard rather than an unpowered USB hub or keyboard passthrough.
  * **User Distance**: Sit 18–30 inches (45–75 cm) directly in front of the screen so the dual IR cameras can capture your eyes.
* **Mouse Cursor Alignment Issues**:
  * Ensure Windows display scaling (DPI) matches your screen resolution, or recalibrate inside TD Control.
