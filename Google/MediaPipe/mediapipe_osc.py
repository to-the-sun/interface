import cv2
import mediapipe as mp
import numpy as np
from pythonosc import udp_client
import time
import os
import sys
import traceback
import urllib.request
import subprocess
import re
import json
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
try:
    import mediapipe.tasks.c
except ImportError:
    pass

# --- Configuration ---
OSC_IP = "127.0.0.1"
BASE_OSC_PORT = 9001
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
TARGET_WEBCAM_NAME = ""
CAMERA_INDEX_OVERRIDE = None # Set to an integer to force a specific camera index

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

MODEL_PATH = resource_path("face_landmarker.task")
CONFIG_FILE = "checkbox_states.json"

def camel_to_snake(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z])([A-Z])', r'\1_\2', s1).lower()

def get_webcam_info():
    names = []
    if sys.platform == "win32":
        try:
            cmds = [
                'wmic path Win32_PnPEntity where "Service=\'usbvideo\'" get Caption',
                'wmic path Win32_PnPEntity where "Category=\'Camera\'" get Caption'
            ]
            for cmd in cmds:
                output = subprocess.check_output(cmd, shell=True).decode()
                lines = [line.strip() for line in output.split('\n') if line.strip() and 'Caption' not in line]
                for line in lines:
                    if line not in names: names.append(line)
        except: pass

    if not names: names = ["MediaPipe_Camera"]

    target_idx = 0
    if TARGET_WEBCAM_NAME:
        for i, name in enumerate(names):
            if TARGET_WEBCAM_NAME.lower() in name.lower():
                target_idx = i
                break

    selected_raw = names[target_idx]
    sanitized = selected_raw.replace(" ", "_").replace("-", "_")
    sanitized = re.sub(r'[^\w]', '', sanitized)

    return names, target_idx, sanitized

ALL_WEBCAMS, CAMERA_INDEX, WEBCAM_NAME = get_webcam_info()
OSC_PORT = BASE_OSC_PORT + CAMERA_INDEX

# --- Processing Helpers ---
def get_pose_params(matrix):
    x, y, z = matrix[0, 3] * 1000, matrix[1, 3] * 1000, matrix[2, 3] * 1000
    sy = np.sqrt(matrix[0,0] * matrix[0,0] +  matrix[1,0] * matrix[1,0])
    if sy > 1e-6:
        pitch = np.arctan2(matrix[2,1] , matrix[2,2])
        yaw = np.arctan2(-matrix[2,0], sy)
        roll = np.arctan2(matrix[1,0], matrix[0,0])
    else:
        pitch = np.arctan2(-matrix[1,2], matrix[1,1])
        yaw = np.arctan2(-matrix[2,0], sy)
        roll = 0
    return [float(x), float(y), float(z), float(np.degrees(pitch)), float(np.degrees(yaw)), float(np.degrees(roll))]

# --- UI & State ---
class Feature:
    def __init__(self, name, address, enabled=True, is_complex=False):
        self.name = name
        self.address = address
        self.enabled = enabled
        self.is_complex = is_complex
        self.current_val = 0.0
        self.max_v = 1.0
        self.ui_rect = None

class AppState:
    def __init__(self):
        self.running = True
        self.client = udp_client.SimpleUDPClient(OSC_IP, OSC_PORT)
        self.features = []
        self.config = self.load_config()
        self.min_detection_confidence = self.config.get("min_detection_confidence", 0.5)
        self.detector_dirty = False
        self.threshold_ui_rects = {}
        self.setup_features()

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
        new_config["min_detection_confidence"] = self.min_detection_confidence
        self.config = new_config
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f)
        except:
            pass

    def setup_features(self):
        pose_names = ["Pose X", "Pose Y", "Pose Z", "Pose Pitch", "Pose Yaw", "Pose Roll"]
        pose_addrs = ["/pose_x", "/pose_y", "/pose_z", "/pose_pitch", "/pose_yaw", "/pose_roll"]
        pose_maxes = [500, 500, 1000, 45, 45, 45]
        for i in range(6):
            enabled = self.config.get(pose_addrs[i], True)
            f = Feature(pose_names[i], pose_addrs[i], enabled)
            f.max_v = pose_maxes[i]
            self.features.append(f)

        self.features.append(Feature("Landmarks", "/landmarks", self.config.get("/landmarks", False), True))
        self.features.append(Feature("Transformation Matrix", "/transformation_matrix", self.config.get("/transformation_matrix", False), True))
        self.features.append(Feature("Detection Confidence Score", "/detection_confidence_score", self.config.get("/detection_confidence_score", True)))
        self.blendshape_init = False

    def init_blendshapes(self, blendshapes):
        for b in blendshapes:
            addr = "/" + camel_to_snake(b.category_name)
            enabled = self.config.get(addr, True)
            self.features.append(Feature(b.category_name, addr, enabled))
        self.blendshape_init = True

state = AppState()

def on_mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        # Check Threshold Buttons
        for btn, rect in state.threshold_ui_rects.items():
            if rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]:
                if btn == "+":
                    state.min_detection_confidence = min(1.0, state.min_detection_confidence + 0.05)
                else:
                    state.min_detection_confidence = max(0.0, state.min_detection_confidence - 0.05)
                state.detector_dirty = True
                state.save_config()
                return

        for f in state.features:
            if f.ui_rect and f.ui_rect[0] <= x <= f.ui_rect[2] and f.ui_rect[1] <= y <= f.ui_rect[3]:
                f.enabled = not f.enabled
                state.save_config()
                break

# --- Mediapipe Setup ---
def setup_detector(min_det_conf=0.5):
    if not os.path.exists(MODEL_PATH):
        print("Downloading face landmarker model...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)

    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=True,
        output_facial_transformation_matrixes=True,
        min_face_detection_confidence=min_det_conf,
        min_face_presence_confidence=min_det_conf,
        running_mode=vision.RunningMode.VIDEO)
    return vision.FaceLandmarker.create_from_options(options)

# --- Main Application ---
def main():
    try:
        print("\n--- Detected Webcams ---")
        for i, cam in enumerate(ALL_WEBCAMS):
            prefix = " [*]" if i == CAMERA_INDEX else " [ ]"
            print(f"{prefix} [{i}] {cam}")

        print(f"\nTarget Webcam: '{TARGET_WEBCAM_NAME}'")

        current_idx = CAMERA_INDEX
        if CAMERA_INDEX_OVERRIDE is not None:
            current_idx = CAMERA_INDEX_OVERRIDE
            print(f"Using Override Index: {current_idx}")

        print(f"Selected Device Index: {current_idx}")
        print(f"Selected Device Name: {ALL_WEBCAMS[current_idx] if current_idx < len(ALL_WEBCAMS) else 'Unknown'}")

        actual_port = BASE_OSC_PORT + current_idx
        state.client = udp_client.SimpleUDPClient(OSC_IP, actual_port)

        print(f"OSC Port: {actual_port} (9001 + Index {current_idx})")
        print(f"OSC Addresses: /eye_blink_left etc.\n")
        print("Press 'n' in the window to cycle to the next camera if the screen is black.")

        detector = setup_detector(state.min_detection_confidence)

        def get_cap(idx):
            if sys.platform == "win32":
                # Try DSHOW first
                c = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                if not c.isOpened():
                    # Fallback to default
                    c = cv2.VideoCapture(idx)
                return c
            else:
                return cv2.VideoCapture(idx)

        cap = get_cap(current_idx)

        if not cap.isOpened():
            print(f"Warning: Could not open camera at index {current_idx}. Trying index 0...")
            current_idx = 0
            cap = get_cap(current_idx)
            if not cap.isOpened():
                raise Exception(f"Could not open any camera.")

        print(f"Camera Initialized: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))} @ {int(cap.get(cv2.CAP_PROP_FPS))} FPS")

        win_name = 'Google MediaPipe'
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win_name, 1420, 480)
        cv2.setMouseCallback(win_name, on_mouse)

        while cap.isOpened() and state.running:
            if state.detector_dirty:
                detector.close()
                detector = setup_detector(state.min_detection_confidence)
                state.detector_dirty = False

            success, image = cap.read()
            if not success: break

            image = cv2.flip(image, 1)
            h, w, _ = image.shape
            timestamp = int(time.time() * 1000)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            result = detector.detect_for_video(mp_image, timestamp)

            display_img = image.copy()
            cv2.putText(display_img, WEBCAM_NAME.replace("_", " "), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            # Threshold UI
            t_txt = f"Min Confidence: {state.min_detection_confidence:.2f}"
            t_size = cv2.getTextSize(t_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            tx = w - t_size[0] - 80
            cv2.putText(display_img, t_txt, (tx, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            # Buttons
            bx1, bx2 = w - 70, w - 40
            cv2.rectangle(display_img, (bx1, 10), (bx1+25, 35), (0, 255, 0), 1)
            cv2.putText(display_img, "-", (bx1+7, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            state.threshold_ui_rects["-"] = [bx1, 10, bx1+25, 35]

            cv2.rectangle(display_img, (bx2, 10), (bx2+25, 35), (0, 255, 0), 1)
            cv2.putText(display_img, "+", (bx2+5, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            state.threshold_ui_rects["+"] = [bx2, 10, bx2+25, 35]

            if result.face_landmarks:
                for landmark in result.face_landmarks[0]:
                    cv2.circle(display_img, (int(landmark.x * w), int(landmark.y * h)), 1, (0, 255, 0), -1)

            # --- Feature Processing & OSC ---
            if result.face_landmarks:
                if not state.blendshape_init and result.face_blendshapes:
                    state.init_blendshapes(result.face_blendshapes[0])

                pose_vals = get_pose_params(result.facial_transformation_matrixes[0])
                for i in range(6):
                    f = state.features[i]
                    f.current_val = pose_vals[i]
                    if f.enabled:
                        state.client.send_message(f.address, float(f.current_val))

                f_lm = state.features[6]
                if f_lm.enabled:
                    l_flat = [float(val) for l in result.face_landmarks[0] for val in [l.x, l.y, l.z]]
                    state.client.send_message(f_lm.address, l_flat)

                f_mx = state.features[7]
                if f_mx.enabled:
                    m_flat = [float(v) for row in result.facial_transformation_matrixes[0] for v in row]
                    state.client.send_message(f_mx.address, m_flat)

                f_det = state.features[8]
                f_det.current_val = 1.0 # If we are here, face is detected
                if f_det.enabled:
                    state.client.send_message(f_det.address, float(f_det.current_val))

                if result.face_blendshapes:
                    bs_offset = 9
                    for i, b in enumerate(result.face_blendshapes[0]):
                        f = state.features[bs_offset + i]
                        f.current_val = b.score
                        if f.enabled:
                            state.client.send_message(f.address, float(b.score))
            else:
                f_det = state.features[8]
                f_det.current_val = 0.0
                if f_det.enabled:
                    state.client.send_message(f_det.address, float(f_det.current_val))

            # --- Rendering UI ---
            sidebar_col_w = 260
            sidebar = np.zeros((h, sidebar_col_w * 3, 3), dtype=np.uint8)
            y_start, y_step, rows_per_col = 20, 15, 30

            for i, f in enumerate(state.features):
                col, row = i // rows_per_col, i % rows_per_col
                tx, ty = 10 + col * sidebar_col_w, y_start + row * y_step
                cb_size = 10
                cv2.rectangle(sidebar, (tx, ty-cb_size), (tx+cb_size, ty), (255,255,255), 1)
                if f.enabled:
                    cv2.rectangle(sidebar, (tx+2, ty-cb_size+2), (tx+cb_size-2, ty-2), (0,255,0), -1)
                f.ui_rect = [w + tx, ty-cb_size, w + tx + sidebar_col_w, ty+5]
                cv2.putText(sidebar, f.name[:20], (tx+15, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
                if not f.is_complex:
                    bar_max_w = sidebar_col_w - 130
                    bar_w = int(min(1.0, abs(f.current_val/f.max_v)) * bar_max_w) if f.max_v != 0 else 0
                    color = (255,100,100) if i < 6 else (0,255,0)
                    cv2.rectangle(sidebar, (tx+120, ty-8), (tx+120+bar_w, ty), color, -1)
                else:
                    cv2.putText(sidebar, "[Complex Data]", (tx+120, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (100, 100, 100), 1)

            cv2.imshow(win_name, np.hstack((display_img, sidebar)))
            key = cv2.waitKey(5) & 0xFF
            if key == 27: break # ESC
            if key == ord('n'): # Cycle camera
                cap.release()
                current_idx = (current_idx + 1) % 10 # Try up to index 9
                print(f"Switching to camera index {current_idx}...")
                cap = get_cap(current_idx)
                actual_port = BASE_OSC_PORT + current_idx
                state.client = udp_client.SimpleUDPClient(OSC_IP, actual_port)
                print(f"New OSC Port: {actual_port}")

            time.sleep(0.001)

        cap.release()
        cv2.destroyAllWindows()

    except Exception:
        traceback.print_exc()
        input("\nPress Enter to close...")

if __name__ == "__main__":
    main()
