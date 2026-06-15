# Google MediaPipe OSC Message Specification

This version of the application streams native MediaPipe Face Landmarker data via OSC.

## Connection Configuration

*   **IP Address:** `127.0.0.1`
*   **Port:** `9001 + Webcam_Index` (e.g., `9001` for the first detected camera, `9002` for the second).
*   **OSC Address Prefix:** None. Messages start directly with the parameter name.

## Dynamic Port Mapping
The application enumerates available webcams on the system. The OSC port is dynamically assigned based on the index of the selected webcam in that list:
`Port = 9001 + Index`

**Note on Camera Switching:** If you press the **'n'** key in the application window to cycle through cameras, the OSC port will automatically update to match the new camera's index.

---

## 1. Facial Blendshapes (52)
Messages are sent as single float values between `0.0` and `1.0`.

**Format:** `/{blendshape_name}` (e.g., `/eye_blink_left`)

---

## 2. Face Landmarks (478)
*   **OSC Address:** `/landmarks`
*   **Format:** A list of 1434 floats: `[x0, y0, z0, ..., z477]`
*   **Default State:** Disabled.

---

## 3. Transformation Matrix
*   **OSC Address:** `/transformation_matrix`
*   **Format:** A list of 16 floats.
*   **Default State:** Disabled.

---

## 4. Decomposed Pose
Head pose parameters are streamed as individual float values.

| OSC Address | Description | Units |
| :--- | :--- | :--- |
| `/pose_x` | Horizontal translation | mm |
| `/pose_y` | Vertical translation | mm |
| `/pose_z` | Depth translation | mm |
| `/pose_pitch` | Pitch rotation | degrees |
| `/pose_yaw` | Yaw rotation | degrees |
| `/pose_roll` | Roll rotation | degrees |
