import cv2
import numpy as np
from pythonosc import udp_client
import time
import os
import sys
import traceback
import json
import math
import tobii_research as tr

# --- Configuration ---
OSC_IP = "127.0.0.1"
OSC_PORT = 9001
CONFIG_FILE = "checkbox_states_tobii.json"

class Feature:
    def __init__(self, name, address, enabled=True, is_complex=False, max_v=1.0):
        self.name = name
        self.address = address
        self.enabled = enabled
        self.is_complex = is_complex
        self.current_val = 0.0
        self.max_v = max_v
        self.ui_rect = None

class AppState:
    def __init__(self):
        self.running = True
        self.client = udp_client.SimpleUDPClient(OSC_IP, OSC_PORT)
        self.features = []
        self.config = self.load_config()
        self.setup_features()
        self.last_gaze_data = None
        self.last_head_pose_data = None
        self.eyetracker = None
        self.all_eyetrackers = []
        self.tracker_index = 0

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def save_config(self):
        new_config = self.config.copy()
        for f in self.features:
            new_config[f.address] = f.enabled
        self.config = new_config
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f)
        except:
            pass

    def setup_features(self):
        # Head Pose features (Mapped to mirror MediaPipe addresses)
        head_feats = [
            ("Pose X", "/pose_x", 500.0),
            ("Pose Y", "/pose_y", 500.0),
            ("Pose Z", "/pose_z", 1000.0),
            ("Pose Pitch", "/pose_pitch", 45.0),
            ("Pose Yaw", "/pose_yaw", 45.0),
            ("Pose Roll", "/pose_roll", 45.0),
        ]
        for name, addr, max_v in head_feats:
            self.features.append(Feature(name, addr, self.config.get(addr, True), max_v=max_v))

        # Gaze features
        gaze_feats = [
            ("Gaze X", "/gaze_x", 1.0),
            ("Gaze Y", "/gaze_y", 1.0),
            ("Left Gaze X", "/left/gaze_x", 1.0),
            ("Left Gaze Y", "/left/gaze_y", 1.0),
            ("Right Gaze X", "/right/gaze_x", 1.0),
            ("Right Gaze Y", "/right/gaze_y", 1.0),
            ("Left Pupil Diameter", "/left/pupil_diameter", 10.0),
            ("Right Pupil Diameter", "/right/pupil_diameter", 10.0),
        ]
        for name, addr, max_v in gaze_feats:
            self.features.append(Feature(name, addr, self.config.get(addr, True), max_v=max_v))

state = AppState()

def on_mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        for f in state.features:
            if f.ui_rect and f.ui_rect[0] <= x <= f.ui_rect[2] and f.ui_rect[1] <= y <= f.ui_rect[3]:
                f.enabled = not f.enabled
                state.save_config()
                break

def gaze_data_callback(gaze_data):
    state.last_gaze_data = gaze_data

    # Use dot notation but fallback to dictionary access to be robust across SDK versions
    try:
        lx, ly = gaze_data.left_gaze_point_on_display_area
        rx, ry = gaze_data.right_gaze_point_on_display_area
        lp = gaze_data.left_pupil_diameter
        rp = gaze_data.right_pupil_diameter
    except (AttributeError, TypeError):
        lx, ly = gaze_data['left_gaze_point_on_display_area']
        rx, ry = gaze_data['right_gaze_point_on_display_area']
        lp = gaze_data['left_pupil_diameter']
        rp = gaze_data['right_pupil_diameter']

    valid_l = not (math.isnan(lx) or math.isnan(ly))
    valid_r = not (math.isnan(rx) or math.isnan(ry))

    # Average Gaze (Indices 6, 7)
    if valid_l and valid_r:
        avg_x = (lx + rx) / 2.0
        avg_y = (ly + ry) / 2.0
        state.features[6].current_val = avg_x
        state.features[7].current_val = avg_y
        if state.features[6].enabled: state.client.send_message(state.features[6].address, float(avg_x))
        if state.features[7].enabled: state.client.send_message(state.features[7].address, float(avg_y))

    # Left Gaze (Indices 8, 9)
    if valid_l:
        state.features[8].current_val = lx
        state.features[9].current_val = ly
        if state.features[8].enabled: state.client.send_message(state.features[8].address, float(lx))
        if state.features[9].enabled: state.client.send_message(state.features[9].address, float(ly))

    # Right Gaze (Indices 10, 11)
    if valid_r:
        state.features[10].current_val = rx
        state.features[11].current_val = ry
        if state.features[10].enabled: state.client.send_message(state.features[10].address, float(rx))
        if state.features[11].enabled: state.client.send_message(state.features[11].address, float(ry))

    # Pupil Diameter (Indices 12, 13)
    if not math.isnan(lp):
        state.features[12].current_val = lp
        if state.features[12].enabled: state.client.send_message(state.features[12].address, float(lp))
    if not math.isnan(rp):
        state.features[13].current_val = rp
        if state.features[13].enabled: state.client.send_message(state.features[13].address, float(rp))

def head_pose_callback(head_pose_data):
    state.last_head_pose_data = head_pose_data

    try:
        pos = head_pose_data.head_position_eye_center
        ori = head_pose_data.head_orientation_rotation_vector
    except (AttributeError, TypeError):
        pos = head_pose_data['head_position_eye_center']
        ori = head_pose_data['head_orientation_rotation_vector']

    if not math.isnan(pos[0]):
        # Mapping to features 0-5. Convert radians to degrees for rotation components.
        vals = [pos[0], pos[1], pos[2], math.degrees(ori[0]), math.degrees(ori[1]), math.degrees(ori[2])]
        for i in range(6):
            f = state.features[i]
            f.current_val = vals[i]
            if f.enabled:
                state.client.send_message(f.address, float(vals[i]))

def main():
    try:
        print("Searching for Tobii eye trackers...")
        state.all_eyetrackers = tr.find_all_eyetrackers()

        if len(state.all_eyetrackers) == 0:
            print("No Tobii eye trackers found!")
            print("Ensure Tobii Core software is running and the device is connected.")
            input("\nPress Enter to exit...")
            return

        def switch_tracker(idx):
            if state.eyetracker:
                state.eyetracker.unsubscribe_from(tr.EYETRACKER_GAZE_DATA)
                try: state.eyetracker.unsubscribe_from(tr.EYETRACKER_HEAD_POSE)
                except: pass

            state.eyetracker = state.all_eyetrackers[idx]
            state.eyetracker.subscribe_to(tr.EYETRACKER_GAZE_DATA, gaze_data_callback)
            try:
                state.eyetracker.subscribe_to(tr.EYETRACKER_HEAD_POSE, head_pose_callback)
                print(f"Subscribed to Head Pose on {state.eyetracker.model}")
            except:
                print(f"Head Pose not supported on {state.eyetracker.model}")

        switch_tracker(0)

        win_name = 'Tobii 4C OSC'
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win_name, 1420, 480)
        cv2.setMouseCallback(win_name, on_mouse)

        w, h = 640, 480

        print(f"Streaming data to {OSC_IP}:{OSC_PORT}")
        print("Press 'n' to cycle through trackers, ESC to exit.")

        while state.running:
            tracker_info = f"{state.eyetracker.model} ({state.eyetracker.serial_number})"
            display_img = np.zeros((h, w, 3), dtype=np.uint8)
            cv2.putText(display_img, tracker_info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Draw Gaze Visualization
            if state.last_gaze_data:
                try:
                    lx, ly = state.last_gaze_data.left_gaze_point_on_display_area
                    rx, ry = state.last_gaze_data.right_gaze_point_on_display_area
                except (AttributeError, TypeError):
                    lx, ly = state.last_gaze_data['left_gaze_point_on_display_area']
                    rx, ry = state.last_gaze_data['right_gaze_point_on_display_area']

                if not (math.isnan(lx) or math.isnan(ly)):
                    cv2.circle(display_img, (int(lx * w), int(ly * h)), 10, (255, 0, 0), 2)
                if not (math.isnan(rx) or math.isnan(ry)):
                    cv2.circle(display_img, (int(rx * w), int(ry * h)), 10, (0, 0, 255), 2)

                if not (math.isnan(lx) or math.isnan(ly)) and not (math.isnan(rx) or math.isnan(ry)):
                    avg_x = (lx + rx) / 2.0
                    avg_y = (ly + ry) / 2.0
                    cv2.drawMarker(display_img, (int(avg_x * w), int(avg_y * h)), (0, 255, 0), cv2.MARKER_CROSS, 20, 2)

            # --- Rendering Sidebar ---
            sidebar_col_w = 260
            sidebar = np.zeros((h, sidebar_col_w * 3, 3), dtype=np.uint8)
            y_start, y_step, rows_per_col = 20, 15, 30

            for i, f in enumerate(state.features):
                col, row = i // rows_per_col, i % rows_per_col
                tx, ty = 10 + col * sidebar_col_w, y_start + row * y_step
                cb_size = 10

                # Checkbox
                cv2.rectangle(sidebar, (tx, ty-cb_size), (tx+cb_size, ty), (255,255,255), 1)
                if f.enabled:
                    cv2.rectangle(sidebar, (tx+2, ty-cb_size+2), (tx+cb_size-2, ty-2), (0,255,0), -1)

                f.ui_rect = [w + tx, ty-cb_size, w + tx + sidebar_col_w, ty+5]
                cv2.putText(sidebar, f.name[:20], (tx+15, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

                # Bar visualization
                bar_max_w = sidebar_col_w - 130
                val_norm = min(1.0, abs(f.current_val / f.max_v)) if f.max_v != 0 else 0
                bar_w = int(val_norm * bar_max_w)
                color = (255,100,100) if "Pose" in f.name else (0,255,0)
                cv2.rectangle(sidebar, (tx+120, ty-8), (tx+120+bar_w, ty), color, -1)

            cv2.imshow(win_name, np.hstack((display_img, sidebar)))
            key = cv2.waitKey(5) & 0xFF
            if key == 27: break # ESC
            if key == ord('n'): # Cycle trackers
                state.tracker_index = (state.tracker_index + 1) % len(state.all_eyetrackers)
                switch_tracker(state.tracker_index)

            time.sleep(0.001)

        state.eyetracker.unsubscribe_from(tr.EYETRACKER_GAZE_DATA)
        try:
            state.eyetracker.unsubscribe_from(tr.EYETRACKER_HEAD_POSE)
        except:
            pass
        cv2.destroyAllWindows()
        print("Successfully unsubscribed and closed.")

    except Exception:
        traceback.print_exc()
        input("\nPress Enter to close...")

if __name__ == "__main__":
    main()
