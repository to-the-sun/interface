# Tobii PCEye 5 to OSC Streamer & Mouse Control

This tool streams real-time gaze data from a **Tobii Dynavox PCEye 5** (or **Tobii Pro** devices) to Open Sound Control (OSC) and moves the onscreen mouse cursor based on gaze position by default.

It supports two gaze input providers:
1. **Tobii Pro SDK (`tobii_research`)**: Native streaming via Tobii Pro SDK (Default).
2. **Microsoft Windows Gaze Input API (`Windows.Devices.Input.Preview`)**: Experimental option using Microsoft's native Windows gaze-input API (`winsdk`) and Windows `SetCursorPos`.

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
- Installs all required dependencies (`tobii-research`, `python-osc`, `pynput`, `winsdk`).
- Launches `tobii_osc.py` with default mouse cursor movement and OSC streaming.

#### Running Microsoft Windows Gaze API Experiment
To test receiving gaze points via Microsoft's `Windows.Devices.Input.Preview` namespace and moving the cursor with `SetCursorPos`:
```cmd
run_tobii.bat --win-gaze
```
Or manually:
```bash
py -3.10 tobii_osc.py --win-gaze
```

#### Manual Execution
If running manually with Python 3.10:
```bash
# 1. Install required dependencies
py -3.10 -m pip install -r requirements.txt

# 2. Run script with default options (Tobii Pro SDK)
py -3.10 tobii_osc.py

# 3. Run script with Windows Gaze Input API experiment
py -3.10 tobii_osc.py --gaze-api win-gaze
```

---

## Features & Options

### Onscreen Mouse Cursor Control
* **Enabled by Default**: The script converts normalized gaze coordinates into screen pixels and moves the Windows/system mouse cursor (`SetCursorPos`) to where you are looking.
* **Disable Mouse Control**: If you only want to stream OSC data without moving the mouse cursor, pass the `--no-mouse` flag:
  ```bash
  py -3.10 tobii_osc.py --no-mouse
  ```

### Command-Line Arguments
| Option | Default | Description |
| :--- | :--- | :--- |
| `--ip` | `127.0.0.1` | OSC Destination IP address |
| `--port` | `6731` | OSC Destination UDP port |
| `--no-mouse` | `False` | Disable moving mouse cursor onscreen using gaze data |
| `--win-gaze` | `False` | Shortcut flag to use Microsoft Windows Gaze Input API (`Windows.Devices.Input.Preview`) |
| `--gaze-api` | `tobii` | Select gaze input provider (`tobii` or `win-gaze`) |
| `--debug` | `False` | Enable verbose per-frame debug logging |

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

### Per-Eye Data (Tobii Pro SDK mode)
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
* **Windows Gaze Input API Access Warning**:
  * If using `--win-gaze`, ensure Eye Tracker access is enabled in Windows Privacy & Security settings (**Settings -> Privacy & Security -> Eye tracker**).
* **"Could not find a version that satisfies the requirement tobii-research"**:
  * The `tobii-research` SDK only provides pre-compiled Python wheels for **Python 3.10** (and 3.8) 64-bit. Python 3.11, 3.12, 3.13+ are NOT supported by Tobii's PyPI package.
  * **Solution**: Run `run_tobii.bat`. It will create an isolated portable Python 3.10 environment automatically.
