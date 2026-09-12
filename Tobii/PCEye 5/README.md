# Tobii PCEye 5 - Windows Gaze Input API to OSC Streamer & Mouse Control

This tool streams real-time gaze data from a **Tobii Dynavox PCEye 5** (or compatible Windows gaze input devices) to Open Sound Control (OSC) and moves the onscreen mouse cursor based on gaze position using Microsoft's native **Windows Gaze Input API** (`Windows.Devices.Input.Preview`) and Windows `SetCursorPos`.

---

## Brand New PCEye 5 Setup Guide (Windows Gaze API)

Follow these step-by-step instructions to set up your PCEye 5 with the Microsoft Windows Gaze Input API.

### Step 1: Hardware Setup & Mounting

1. **Unbox the PCEye 5**: Remove the PCEye 5 tracker bar, USB extension cable, and magnetic mounting plates.
2. **Mount the Bracket**: Firmly press the magnetic mounting plate onto the center of the bottom screen bezel for at least 30 seconds.
3. **Attach & Plug in**: Snap the PCEye 5 bar onto the magnetic mounting bracket and plug the USB-A cable directly into a powered USB port.

---

### Step 2: Tobii Software & Windows Eye Tracker Settings

1. **Install TD Control / PCEye Software**:
   - Download and install **TD Control** from Tobii Dynavox to install device drivers.
2. **Enable Windows Eye Tracking**:
   - Open **Windows Settings** -> **Privacy & Security** (or **Devices**) -> **Eye tracker**.
   - Ensure Eye Tracking and app permissions are enabled for Windows Gaze input access.
3. **Calibrate**: Perform eye calibration inside **TD Control**.

---

### Step 3: Running the OSC Streamer & Mouse Control

#### Quick Start (Automated Environment)
Simply double-click or run the batch script on Windows:
```cmd
run_tobii.bat
```
`run_tobii.bat` automatically checks/sets up the Python environment, installs dependencies (`python-osc`, `pynput`, `winsdk`), and launches `tobii_osc.py`.

#### Manual Execution
```bash
# 1. Install required dependencies
pip install -r requirements.txt

# 2. Run script
python tobii_osc.py
```

---

## Features & Options

### Onscreen Mouse Cursor Control
* **Enabled by Default**: Converts Windows Gaze coordinates into screen pixels and moves the mouse cursor using Windows `SetCursorPos`.
* **Disable Mouse Control**: Pass `--no-mouse` to stream OSC data without moving the cursor:
  ```bash
  python tobii_osc.py --no-mouse
  ```

### Command-Line Arguments
| Option | Default | Description |
| :--- | :--- | :--- |
| `--ip` | `127.0.0.1` | OSC Destination IP address |
| `--port` | `6731` | OSC Destination UDP port |
| `--no-mouse` | `False` | Disable moving mouse cursor onscreen using gaze data |
| `--debug` | `False` | Enable verbose per-frame debug logging |

---

## OSC Message Mapping

The script streams data to the following OSC addresses:

### Primary Gaze
* `/Tobii/gaze_x`: Horizontal gaze position (0.0 = Left edge, 1.0 = Right edge)
* `/Tobii/gaze_y`: Vertical gaze position (0.0 = Top edge, 1.0 = Bottom edge)

### OpenFace Compatibility
* `/OpenFace/gaze_left_right`: Approximate gaze angle in degrees (-30 to 30)
* `/OpenFace/gaze_up_down`: Approximate gaze angle in degrees (-30 to 30)
