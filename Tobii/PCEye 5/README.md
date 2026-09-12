# Tobii PCEye 5 - Windows Gaze Input API to OSC Streamer & Mouse Control

This project streams real-time gaze data from a **Tobii Dynavox PCEye 5** (or compatible Windows gaze input devices) to Open Sound Control (OSC) and moves the onscreen mouse cursor continuously using Microsoft's native **Windows Gaze Input API** (`Windows.Devices.Input.Preview`) and Windows `SetCursorPos`.

Both **C# (.NET 8)** and **Python (`winsdk`)** implementations are provided in this folder.

---

## Windows Eye Control & Driver Setup Guide

You **cannot manually register** an eye tracker as a Windows gaze device. The manufacturer's driver/software must expose it to Windows through the Windows Eye Control / gaze-input interface.

### Step 1: Install Official PCEye 5 Software & Driver

1. Disconnect the PCEye 5 USB cable if prompted by the installer.
2. Download the official **PCEye 5 Software Installer** (includes **TD Control**) from Tobii Dynavox:
   - [PCEye 5 Software Installer](https://www.mytobiidynavox.com/Support/pceyecc)
3. Run `TDControl_Setup.exe` and approve the UAC prompt.
4. Finish installation and plug the PCEye 5 directly into a powered USB port (avoid unpowered USB hubs).

### Step 2: Confirm Device Detection in TD Control

1. Launch **TD Control** from the Windows Start menu.
2. Confirm live eye tracking status and complete full eye calibration in your normal seated position (18–30 inches from monitor).

### Step 3: Enable Windows Eye Control & Run Diagnostic Test

1. Open **Windows Settings** (`Win + I`).
2. Go to **Ease of Access** -> **Eye control** (left sidebar).
3. Toggle **Eye control** to **On**.
4. Observe the screen:
   - **Result A**: A **moving red dot** appears following your gaze. This proves Windows is receiving live gaze input from the PCEye 5!
   - **Result B**: Eye control is grayed out or reports no compatible device.

#### Diagnostic Outcomes

| What You See | What It Means | Next Step |
| :--- | :--- | :--- |
| **Eye control turns on & red dot moves** | Windows receives live gaze input | Run `run_tobii.bat` to launch continuous `SetCursorPos` mouse streamer |
| **Eye control says no compatible device** | Driver does not publish to Windows Gaze API | Ensure TD Control is installed and calibrated |
| **No Eye control setting page** | Windows edition/version missing component | Update Windows 10/11 |

---

## Why the Windows Mouse Pointer Doesn't Follow by Default

Windows Eye Control uses a **dwell-based launchpad** (Precise Mouse) so the mouse arrow doesn't jump whenever you look around.

Our custom project subscribes directly to `Windows.Devices.Input.Preview.GazeInputSourcePreview` and calls `SetCursorPos(px, py)` on every gaze event, giving you **continuous real-time mouse tracking**:

```text
PCEye 5 -> Windows Gaze API -> GazeMoved event -> SetCursorPos(x, y)
```

---

## How to Run

### Quick Start (Double-Click Batch Script)
Simply double-click or run:
```cmd
run_tobii.bat
```
`run_tobii.bat` will:
1. Automatically build and run the high-performance **C# application** (`Program.cs`) if `.NET SDK` is installed.
2. Automatically fallback to the **Python environment** (`tobii_osc.py` using `winsdk`) if `.NET SDK` is not installed.

### Manual C# (.NET 8) Execution
```cmd
dotnet run -c Release
```

### Manual Python Execution
```bash
pip install -r requirements.txt
python tobii_osc.py
```

---

## Features & Command-Line Arguments

| Option | Default | Description |
| :--- | :--- | :--- |
| `--ip` | `127.0.0.1` | OSC Destination IP address |
| `--port` | `6731` | OSC Destination UDP port |
| `--no-mouse` | `False` | Disable moving mouse cursor onscreen using gaze data |

---

## OSC Message Mapping

* `/Tobii/gaze_x`: Horizontal gaze position (0.0 = Left edge, 1.0 = Right edge)
* `/Tobii/gaze_y`: Vertical gaze position (0.0 = Top edge, 1.0 = Bottom edge)
* `/OpenFace/gaze_left_right`: Approximate gaze angle in degrees (-30 to 30)
* `/OpenFace/gaze_up_down`: Approximate gaze angle in degrees (-30 to 30)
