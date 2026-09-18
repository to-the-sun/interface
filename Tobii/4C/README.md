# Tobii 4C OSC Streamer & Mouse Controller (Stream Engine API)

Real-time gaze and head pose OSC streamer and mouse controller for the **Tobii Eye Tracker 4C** (and compatible Tobii hardware).

This tool connects directly to Tobii's native C API (**Tobii Stream Engine**) using Python `ctypes`, completely removing the need for `tobii-research` (Tobii Pro SDK) or special Pro licensing upgrades.

---

## Key Features

- **Direct Tobii Stream Engine Integration**: Accesses low-level gaze and head pose data directly via `tobii_stream_engine.dll` (Windows), `libtobii_stream_engine.so` (Linux), or `libtobii_stream_engine.dylib` (macOS).
- **Automated 32-Bit Python Setup**: Includes `run_tobii_4c.bat`, which automatically locates a system 32-bit Python runtime or downloads and configures an isolated local 32-bit Python 3.10 environment (`env_32`) required for the 32-bit Tobii Stream Engine DLL.
- **Continuous Mouse Cursor Control**: Maps normalized gaze coordinates (0.0 to 1.0) directly to screen coordinates using Windows high-performance DPI-aware `SetCursorPos` with `pynput` fallback.
- **UAC Admin Privilege Elevation**: Automatically requests Windows UAC administrator privileges on startup so gaze mouse control works seamlessly in restricted/elevated windows (e.g., Task Manager, elevated terminals, games).
- **Auto-Minimization on Startup**: Automatically minimizes its console and OpenCV GUI windows on launch to stay out of the way during operation while remaining running in the background.
- **Background TCP Command Server**: Runs an internal TCP control server on port `10003` to toggle mouse control dynamically from external applications or scripts (such as `midi_to_input.py`).
- **Interactive OpenCV GUI & Control Sidebar**: Provides real-time visual gaze tracking overlays and clickable sidebar checkboxes to toggle individual OSC addresses and mouse control on/off.
- **State Persistence**: Automatically persists individual feature toggles and mouse control status to `checkbox_states_tobii.json`.

---

## System Requirements & Prerequisites

1. **Tobii Core Software / Eye Tracking Service**: Tobii Core software or Tobii Eye Tracking Service must be installed and running on Windows.
2. **Tobii Eye Tracker 4C**: Plugged into a powered USB port and calibrated via Tobii Core software.
3. **Python Runtime**:
   - **Recommended**: Simply double-click `run_tobii_4c.bat` on Windows.
   - **Manual Execution**: Requires a 32-bit Python environment on Windows (Python 3.8 to 3.12+) because `tobii_stream_engine.dll` is 32-bit.

---

## How to Run

### 1. Quick Launch (Windows Batch Script - Recommended)
Double-click `run_tobii_4c.bat` in the `Tobii/4C/` directory.

`run_tobii_4c.bat` handles everything automatically:
1. Searches system PATH and Python launcher (`py -3-32`) for a 32-bit Python runtime.
2. If no 32-bit Python is installed, it downloads Python 3.10 32-bit embeddable zip, extracts it to `Tobii/4C/env_32`, installs `pip`, and installs all dependencies from `requirements.txt`.
3. Requests UAC elevation (if needed) and executes `tobii_4c_osc.py`.

### 2. Manual Command Line Execution
If running manually in a 32-bit Python shell:
```bash
pip install -r requirements.txt
python tobii_4c_osc.py
```

---

## Command Line Arguments

| Argument | Default | Description |
| :--- | :--- | :--- |
| `--ip` | `127.0.0.1` | Destination IP address for OSC messages |
| `--port` | `6733` | Destination UDP port for OSC messages |
| `--tcp-port` | `10003` | Port for the background TCP command server |
| `--no-mouse` | `False` | Disable automatic gaze-based mouse cursor movement on launch |
| `--no-elevate` | `False` | Disable automatic Windows UAC Administrator elevation request |

---

## Remote TCP Control Server

The script listens for incoming TCP text commands on `127.0.0.1:10003` (or `--tcp-port`). You can send TCP messages to toggle or query mouse control state:

| Command | Action |
| :--- | :--- |
| `on` / `1` / `true` / `enable` | Enable mouse control |
| `off` / `0` / `false` / `disable` | Disable mouse control |
| `toggle` / `m` / `switch` | Toggle mouse control state |
| `status` / `get` | Query current mouse control state |

*Example usage via PowerShell*:
```powershell
$client = New-Object System.Net.Sockets.TcpClient("127.0.0.1", 10003)
$stream = $client.GetStream()
$bytes = [System.Text.Encoding]::ASCII.GetBytes("toggle`n")
$stream.Write($bytes, 0, $bytes.Length)
$client.Close()
```

---

## Interactive Controls & Hotkeys

- **Sidebar Checkboxes**: Click any checkbox in the right sidebar of the GUI window to enable/disable streaming for that specific OSC address.
- **Mouse Control Toggle Button**: Click the green/red box next to "Mouse control" at the top-left of the visualizer to toggle mouse control.
- **Keyboard Shortcuts**:
  - `m`: Toggle mouse control ON or OFF.
  - `n`: Cycle through connected Tobii eye tracking devices.
  - `ESC`: Exit application cleanly.

---

## OSC Message Mapping

OSC messages are streamed over UDP to `127.0.0.1:6733` by default (addresses mirror MediaPipe OSC formatting):

### Head Pose
| Address | Data Range / Unit | Description |
| :--- | :--- | :--- |
| `/pose_x` | Position (mm) | Head horizontal offset |
| `/pose_y` | Position (mm) | Head vertical offset |
| `/pose_z` | Position (mm) | Head depth/distance offset |
| `/pose_pitch` | Degrees (-45 to 45) | Head pitch rotation |
| `/pose_yaw` | Degrees (-45 to 45) | Head yaw rotation |
| `/pose_roll` | Degrees (-45 to 45) | Head roll rotation |

### Gaze & Pupil Metrics
| Address | Data Range / Unit | Description |
| :--- | :--- | :--- |
| `/gaze_x` | `0.0` - `1.0` | Average normalized horizontal gaze position |
| `/gaze_y` | `0.0` - `1.0` | Average normalized vertical gaze position |
| `/left/gaze_x` | `0.0` - `1.0` | Left eye normalized horizontal gaze |
| `/left/gaze_y` | `0.0` - `1.0` | Left eye normalized vertical gaze |
| `/right/gaze_x` | `0.0` - `1.0` | Right eye normalized horizontal gaze |
| `/right/gaze_y` | `0.0` - `1.0` | Right eye normalized vertical gaze |
| `/left/pupil_diameter` | Diameter (mm) | Left pupil size |
| `/right/pupil_diameter` | Diameter (mm) | Right pupil size |

---

## Diagnostics & Troubleshooting

- **"Could not load tobii_stream_engine.dll"**:
  - **Architecture Mismatch**: `tobii_stream_engine.dll` is 32-bit. Ensure you are running 32-bit Python or using `run_tobii_4c.bat` (which builds `env_32` automatically).
  - **Tobii Core Software**: Ensure Tobii Core software / Tobii Service is installed and active in the system tray.
- **"No Tobii eye trackers found via Tobii Stream Engine API"**:
  - Check USB connections (use motherboard back ports, avoiding unpowered USB hubs).
  - Open Tobii Eye Tracking Core software and confirm eye calibration is functioning.
- **Mouse cursor does not move inside certain windows**:
  - Ensure administrative privileges were granted. Launching via `run_tobii_4c.bat` auto-elevates privileges. If disabled with `--no-elevate`, run the command prompt as Administrator.
