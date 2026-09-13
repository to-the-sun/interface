import sys
import time
import os
import ctypes
import ctypes.util
from ctypes import c_int, c_uint32, c_int64, c_float, c_char_p, c_void_p, POINTER, Structure, CFUNCTYPE, byref
import traceback
import json
import math
import argparse

# Dependency checks for OpenCV and Python-OSC
try:
    import cv2
    import numpy as np
    from pythonosc import udp_client
except (ImportError, ModuleNotFoundError) as e:
    print("=" * 72)
    print(f"ERROR: Missing required dependency ({getattr(e, 'name', str(e))}).")
    print("Please install required dependencies with:")
    print("  pip install -r requirements.txt")
    print("=" * 72)
    if sys.platform == "win32":
        input("\nPress Enter to exit...")
    sys.exit(1)

# Mouse fallback controller
try:
    from pynput.mouse import Controller as MouseController
    mouse_controller = MouseController()
except Exception:
    mouse_controller = None

# --- Tobii Stream Engine C API Definitions ---
TOBII_ERROR_NO_ERROR = 0

class TobiiValidity:
    TOBII_VALIDITY_INVALID = 0
    TOBII_VALIDITY_VALID = 1

class TobiiFieldOfUse:
    TOBII_FIELD_OF_USE_DEFAULT = 0
    TOBII_FIELD_OF_USE_INTERACTIVE = 1
    TOBII_FIELD_OF_USE_ANALYTICAL = 2

class tobii_gaze_point_t(Structure):
    _fields_ = [
        ("timestamp_us", c_int64),
        ("validity", c_int),
        ("position_xy", c_float * 2),
    ]

class tobii_gaze_data_t(Structure):
    _fields_ = [
        ("timestamp_us", c_int64),
        ("left_gaze_point_validity", c_int),
        ("left_gaze_point_on_display_normalized", c_float * 2),
        ("left_gaze_origin_validity", c_int),
        ("left_gaze_origin_in_user_coordinate_system_mm", c_float * 3),
        ("left_pupil_validity", c_int),
        ("left_pupil_diameter_mm", c_float),
        ("right_gaze_point_validity", c_int),
        ("right_gaze_point_on_display_normalized", c_float * 2),
        ("right_gaze_origin_validity", c_int),
        ("right_gaze_origin_in_user_coordinate_system_mm", c_float * 3),
        ("right_pupil_validity", c_int),
        ("right_pupil_diameter_mm", c_float),
    ]

class tobii_head_pose_t(Structure):
    _fields_ = [
        ("timestamp_us", c_int64),
        ("position_validity", c_int),
        ("position_xyz", c_float * 3),
        ("rotation_validity", c_int),
        ("rotation_xyz", c_float * 3),
    ]

# Callback C Function Types
tobii_url_receiver_t = CFUNCTYPE(None, c_char_p, c_void_p)
tobii_gaze_point_callback_t = CFUNCTYPE(None, POINTER(tobii_gaze_point_t), c_void_p)
tobii_gaze_data_callback_t = CFUNCTYPE(None, POINTER(tobii_gaze_data_t), c_void_p)
tobii_head_pose_callback_t = CFUNCTYPE(None, POINTER(tobii_head_pose_t), c_void_p)


def load_tobii_stream_engine():
    """Attempts to locate and load the Tobii Stream Engine shared library / DLL."""
    lib_names = []
    if sys.platform == "win32":
        lib_names = ["tobii_stream_engine.dll", "libtobii_stream_engine.dll"]
    elif sys.platform == "darwin":
        lib_names = ["libtobii_stream_engine.dylib"]
    else:
        lib_names = ["libtobii_stream_engine.so"]

    search_dirs = [
        os.path.dirname(os.path.abspath(__file__)),
        os.getcwd(),
        r"C:\Program Files\Tobii\Tobii EyeX",
        r"C:\Program Files (x86)\Tobii\Tobii EyeX",
        r"C:\Program Files\Tobii\Tobii Stream Engine",
        r"C:\Program Files (x86)\Tobii\Tobii Stream Engine",
        r"C:\Program Files\Tobii\Tobii Eye Tracker Core Software",
        r"C:\Program Files (x86)\Tobii\Tobii Eye Tracker Core Software",
        r"C:\Program Files\Tobii\Tobii Core Software",
        r"C:\Program Files (x86)\Tobii\Tobii Core Software",
        r"C:\Program Files\Tobii\Tobii Service",
        r"C:\Program Files (x86)\Tobii\Tobii Service",
    ]

    last_errors = []

    for d in search_dirs:
        for name in lib_names:
            full_path = os.path.join(d, name)
            if os.path.exists(full_path):
                if sys.platform == "win32":
                    if hasattr(os, "add_dll_directory"):
                        try:
                            os.add_dll_directory(d)
                        except Exception:
                            pass
                    # Add directory to PATH so dependent DLLs can be located
                    if d not in os.environ.get("PATH", "").split(os.path.pathsep):
                        os.environ["PATH"] = d + os.path.pathsep + os.environ.get("PATH", "")

                try:
                    return ctypes.CDLL(full_path)
                except Exception as err:
                    last_errors.append(f"Found '{full_path}' but failed to load (CDLL): {err}")
                    if sys.platform == "win32":
                        try:
                            return ctypes.WinDLL(full_path)
                        except Exception as win_err:
                            last_errors.append(f"Found '{full_path}' but failed to load (WinDLL): {win_err}")

    # Try standard system load
    for name in lib_names:
        try:
            return ctypes.CDLL(name)
        except Exception as err:
            last_errors.append(f"System load '{name}' failed: {err}")

    found_lib = ctypes.util.find_library("tobii_stream_engine")
    if found_lib:
        try:
            return ctypes.CDLL(found_lib)
        except Exception as err:
            last_errors.append(f"find_library '{found_lib}' failed to load: {err}")

    if last_errors:
        print("\nDLL Loader Diagnostic Log:")
        for err in last_errors:
            print(f" - {err}")

    return None


# Binding Stream Engine Library API
class TobiiStreamEngineAPI:
    def __init__(self, lib):
        self.lib = lib
        if not self.lib:
            return

        # tobii_error_message
        self.tobii_error_message = getattr(self.lib, "tobii_error_message", None)
        if self.tobii_error_message:
            self.tobii_error_message.argtypes = [c_int]
            self.tobii_error_message.restype = c_char_p

        # tobii_api_create
        self.tobii_api_create = getattr(self.lib, "tobii_api_create", None)
        if self.tobii_api_create:
            self.tobii_api_create.argtypes = [POINTER(c_void_p), c_void_p, c_void_p]
            self.tobii_api_create.restype = c_int

        # tobii_api_destroy
        self.tobii_api_destroy = getattr(self.lib, "tobii_api_destroy", None)
        if self.tobii_api_destroy:
            self.tobii_api_destroy.argtypes = [c_void_p]
            self.tobii_api_destroy.restype = c_int

        # tobii_enumerate_local_device_urls
        self.tobii_enumerate_local_device_urls = getattr(self.lib, "tobii_enumerate_local_device_urls", None)
        if self.tobii_enumerate_local_device_urls:
            self.tobii_enumerate_local_device_urls.argtypes = [c_void_p, tobii_url_receiver_t, c_void_p]
            self.tobii_enumerate_local_device_urls.restype = c_int

        # tobii_device_create raw reference
        self.raw_tobii_device_create = getattr(self.lib, "tobii_device_create", None)

        # tobii_device_destroy
        self.tobii_device_destroy = getattr(self.lib, "tobii_device_destroy", None)
        if self.tobii_device_destroy:
            self.tobii_device_destroy.argtypes = [c_void_p]
            self.tobii_device_destroy.restype = c_int

        # tobii_device_process_callbacks
        self.tobii_device_process_callbacks = getattr(self.lib, "tobii_device_process_callbacks", None)
        if self.tobii_device_process_callbacks:
            self.tobii_device_process_callbacks.argtypes = [c_void_p]
            self.tobii_device_process_callbacks.restype = c_int

        # tobii_gaze_point_subscribe
        self.tobii_gaze_point_subscribe = getattr(self.lib, "tobii_gaze_point_subscribe", None)
        if self.tobii_gaze_point_subscribe:
            self.tobii_gaze_point_subscribe.argtypes = [c_void_p, tobii_gaze_point_callback_t, c_void_p]
            self.tobii_gaze_point_subscribe.restype = c_int

        # tobii_gaze_point_unsubscribe
        self.tobii_gaze_point_unsubscribe = getattr(self.lib, "tobii_gaze_point_unsubscribe", None)
        if self.tobii_gaze_point_unsubscribe:
            self.tobii_gaze_point_unsubscribe.argtypes = [c_void_p]
            self.tobii_gaze_point_unsubscribe.restype = c_int

        # tobii_gaze_data_subscribe
        self.tobii_gaze_data_subscribe = getattr(self.lib, "tobii_gaze_data_subscribe", None)
        if self.tobii_gaze_data_subscribe:
            self.tobii_gaze_data_subscribe.argtypes = [c_void_p, tobii_gaze_data_callback_t, c_void_p]
            self.tobii_gaze_data_subscribe.restype = c_int

        # tobii_gaze_data_unsubscribe
        self.tobii_gaze_data_unsubscribe = getattr(self.lib, "tobii_gaze_data_unsubscribe", None)
        if self.tobii_gaze_data_unsubscribe:
            self.tobii_gaze_data_unsubscribe.argtypes = [c_void_p]
            self.tobii_gaze_data_unsubscribe.restype = c_int

        # tobii_head_pose_subscribe
        self.tobii_head_pose_subscribe = getattr(self.lib, "tobii_head_pose_subscribe", None)
        if self.tobii_head_pose_subscribe:
            self.tobii_head_pose_subscribe.argtypes = [c_void_p, tobii_head_pose_callback_t, c_void_p]
            self.tobii_head_pose_subscribe.restype = c_int

        # tobii_head_pose_unsubscribe
        self.tobii_head_pose_unsubscribe = getattr(self.lib, "tobii_head_pose_unsubscribe", None)
        if self.tobii_head_pose_unsubscribe:
            self.tobii_head_pose_unsubscribe.argtypes = [c_void_p]
            self.tobii_head_pose_unsubscribe.restype = c_int

    def create_device(self, api_handle, url_bytes, dev_ptr):
        if not self.raw_tobii_device_create:
            return TOBII_ERROR_NO_ERROR - 1

        attempts = []

        # Candidate URLs: Specific device URL bytes, None (for default device)
        url_candidates = [url_bytes, None]

        for u in url_candidates:
            # Variant A: 3 parameters (api_handle, url, device_ptr)
            try:
                self.raw_tobii_device_create.argtypes = [c_void_p, c_char_p, POINTER(c_void_p)]
                self.raw_tobii_device_create.restype = c_int
                ret = self.raw_tobii_device_create(api_handle, u, byref(dev_ptr))
                if ret == TOBII_ERROR_NO_ERROR and dev_ptr.value:
                    return ret
                attempts.append(f"3-param (url={'default' if u is None else u.decode('utf-8', 'ignore')}): code {ret} ({self.get_error_str(ret)})")
            except Exception as e:
                attempts.append(f"3-param exception: {e}")

            # Variant B: 4 parameters with field of use INTERACTIVE (1)
            try:
                self.raw_tobii_device_create.argtypes = [c_void_p, c_char_p, c_int, POINTER(c_void_p)]
                self.raw_tobii_device_create.restype = c_int
                ret = self.raw_tobii_device_create(api_handle, u, TobiiFieldOfUse.TOBII_FIELD_OF_USE_INTERACTIVE, byref(dev_ptr))
                if ret == TOBII_ERROR_NO_ERROR and dev_ptr.value:
                    return ret
                attempts.append(f"4-param INTERACTIVE (url={'default' if u is None else u.decode('utf-8', 'ignore')}): code {ret} ({self.get_error_str(ret)})")
            except Exception as e:
                attempts.append(f"4-param INTERACTIVE exception: {e}")

            # Variant C: 4 parameters with field of use DEFAULT (0)
            try:
                self.raw_tobii_device_create.argtypes = [c_void_p, c_char_p, c_int, POINTER(c_void_p)]
                self.raw_tobii_device_create.restype = c_int
                ret = self.raw_tobii_device_create(api_handle, u, TobiiFieldOfUse.TOBII_FIELD_OF_USE_DEFAULT, byref(dev_ptr))
                if ret == TOBII_ERROR_NO_ERROR and dev_ptr.value:
                    return ret
                attempts.append(f"4-param DEFAULT (url={'default' if u is None else u.decode('utf-8', 'ignore')}): code {ret} ({self.get_error_str(ret)})")
            except Exception as e:
                attempts.append(f"4-param DEFAULT exception: {e}")

        print("\n[Device Create Diagnostic Attempts]:")
        for att in attempts:
            print(f" - {att}")

        return -1

    def get_error_str(self, err_code):
        if self.tobii_error_message:
            try:
                msg = self.tobii_error_message(err_code)
                if msg:
                    return msg.decode('utf-8')
            except Exception:
                pass
        return f"Error code {err_code}"


# Administrator privileges and window minimization helpers
def is_admin():
    """Checks if the script is running with administrator privileges."""
    if sys.platform != 'win32':
        return True
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def elevate_privileges():
    """Restarts the script with administrator privileges if on Windows and not already admin."""
    if sys.platform == 'win32' and not is_admin():
        import ctypes
        print("[*] Detected non-administrator execution.")
        print("[*] Administrative privileges are required to move mouse inside restricted windows like Task Manager.")
        print("[*] Elevating privileges via Windows UAC Prompt...")
        time.sleep(1.0)

        script = os.path.abspath(sys.argv[0])
        params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])

        try:
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)
            if int(ret) > 32:
                sys.exit(0)
            else:
                print(f"[!] UAC Elevation failed with return code {ret}.")
        except Exception as e:
            print(f"[!] UAC Elevation failed: {e}")
            print("[*] Continuing without administrator privileges...")

def minimize_console_window():
    """Minimizes the Python console window on Windows."""
    if sys.platform == "win32":
        try:
            import ctypes
            console_hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if console_hwnd:
                ctypes.windll.user32.ShowWindow(console_hwnd, 6)  # 6 = SW_MINIMIZE
        except Exception as e:
            print(f"[*] Failed to minimize console window: {e}")

def minimize_gui_window(win_name):
    """Minimizes an OpenCV GUI window by window title on Windows."""
    if sys.platform == "win32":
        try:
            import ctypes
            gui_hwnd = ctypes.windll.user32.FindWindowW(None, win_name)
            if gui_hwnd:
                ctypes.windll.user32.ShowWindow(gui_hwnd, 6)  # 6 = SW_MINIMIZE
        except Exception as e:
            print(f"[*] Failed to minimize GUI window '{win_name}': {e}")

# --- Configuration ---
OSC_IP = "127.0.0.1"
OSC_PORT = 9002
CONFIG_FILE = "checkbox_states_tobii.json"

def get_screen_size():
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            try:
                user32.SetProcessDPIAware()
            except Exception:
                pass
            w, h = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
            if w > 0 and h > 0:
                return w, h
        except Exception:
            pass
    try:
        import tkinter
        root = tkinter.Tk()
        root.withdraw()
        w = root.winfo_screenwidth()
        h = root.winfo_screenheight()
        root.destroy()
        if w > 0 and h > 0:
            return w, h
    except Exception:
        pass
    return 1920, 1080

def set_cursor_pos(px, py):
    """
    Sets system mouse cursor position using Windows SetCursorPos API (ctypes)
    or pynput fallback.
    """
    if sys.platform == "win32":
        try:
            import ctypes
            if ctypes.windll.user32.SetCursorPos(int(px), int(py)):
                return True
        except Exception:
            pass
    if mouse_controller is not None:
        try:
            mouse_controller.position = (int(px), int(py))
            return True
        except Exception:
            pass
    return False

def move_cursor_to_gaze(gx, gy):
    if not state.move_mouse or math.isnan(gx) or math.isnan(gy):
        return False
    sw, sh = state.screen_size
    px = max(0.0, min(1.0, float(gx))) * sw
    py = max(0.0, min(1.0, float(gy))) * sh
    return set_cursor_pos(px, py)

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
        self.move_mouse = self.config.get("move_mouse", True)
        self.screen_size = get_screen_size()
        self.setup_features()
        self.last_gaze_data = None
        self.last_head_pose_data = None
        self.device_urls = []
        self.current_device_url = None
        self.api_handle = None
        self.device_handle = None
        self.tracker_index = 0
        self.c_gaze_data_cb = None
        self.c_gaze_point_cb = None
        self.c_head_pose_cb = None
        self.c_url_cb = None

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_config(self):
        new_config = self.config.copy()
        for f in self.features:
            new_config[f.address] = f.enabled
        new_config["move_mouse"] = self.move_mouse
        self.config = new_config
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f)
        except Exception:
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

def on_gaze_point(gaze_point_ptr, user_data):
    if not gaze_point_ptr:
        return
    gp = gaze_point_ptr.contents
    if gp.validity == TobiiValidity.TOBII_VALIDITY_VALID:
        gx, gy = float(gp.position_xy[0]), float(gp.position_xy[1])
        state.last_gaze_data = {'left_gaze_point_on_display_area': (gx, gy), 'right_gaze_point_on_display_area': (gx, gy)}

        state.features[6].current_val = gx
        state.features[7].current_val = gy
        if state.features[6].enabled: state.client.send_message(state.features[6].address, gx)
        if state.features[7].enabled: state.client.send_message(state.features[7].address, gy)

        move_cursor_to_gaze(gx, gy)

def on_gaze_data(gaze_data_ptr, user_data):
    if not gaze_data_ptr:
        return
    gd = gaze_data_ptr.contents

    valid_l = (gd.left_gaze_point_validity == TobiiValidity.TOBII_VALIDITY_VALID)
    valid_r = (gd.right_gaze_point_validity == TobiiValidity.TOBII_VALIDITY_VALID)

    lx = float(gd.left_gaze_point_on_display_normalized[0]) if valid_l else float('nan')
    ly = float(gd.left_gaze_point_on_display_normalized[1]) if valid_l else float('nan')
    rx = float(gd.right_gaze_point_on_display_normalized[0]) if valid_r else float('nan')
    ry = float(gd.right_gaze_point_on_display_normalized[1]) if valid_r else float('nan')
    lp = float(gd.left_pupil_diameter_mm) if gd.left_pupil_validity == TobiiValidity.TOBII_VALIDITY_VALID else float('nan')
    rp = float(gd.right_pupil_diameter_mm) if gd.right_pupil_validity == TobiiValidity.TOBII_VALIDITY_VALID else float('nan')

    state.last_gaze_data = {
        'left_gaze_point_on_display_area': (lx, ly),
        'right_gaze_point_on_display_area': (rx, ry),
        'left_pupil_diameter': lp,
        'right_pupil_diameter': rp
    }

    gaze_x, gaze_y = None, None

    # Average Gaze (Indices 6, 7)
    if valid_l and valid_r:
        avg_x = (lx + rx) / 2.0
        avg_y = (ly + ry) / 2.0
        gaze_x, gaze_y = avg_x, avg_y
        state.features[6].current_val = avg_x
        state.features[7].current_val = avg_y
        if state.features[6].enabled: state.client.send_message(state.features[6].address, float(avg_x))
        if state.features[7].enabled: state.client.send_message(state.features[7].address, float(avg_y))
    elif valid_l:
        gaze_x, gaze_y = lx, ly
        state.features[6].current_val = lx
        state.features[7].current_val = ly
        if state.features[6].enabled: state.client.send_message(state.features[6].address, float(lx))
        if state.features[7].enabled: state.client.send_message(state.features[7].address, float(ly))
    elif valid_r:
        gaze_x, gaze_y = rx, ry
        state.features[6].current_val = rx
        state.features[7].current_val = ry
        if state.features[6].enabled: state.client.send_message(state.features[6].address, float(rx))
        if state.features[7].enabled: state.client.send_message(state.features[7].address, float(ry))

    if gaze_x is not None and gaze_y is not None:
        move_cursor_to_gaze(gaze_x, gaze_y)

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

def on_head_pose(head_pose_ptr, user_data):
    if not head_pose_ptr:
        return
    hp = head_pose_ptr.contents

    pos_valid = (hp.position_validity == TobiiValidity.TOBII_VALIDITY_VALID)
    rot_valid = (hp.rotation_validity == TobiiValidity.TOBII_VALIDITY_VALID)

    px = float(hp.position_xyz[0]) if pos_valid else 0.0
    py = float(hp.position_xyz[1]) if pos_valid else 0.0
    pz = float(hp.position_xyz[2]) if pos_valid else 0.0

    rx = math.degrees(float(hp.rotation_xyz[0])) if rot_valid else 0.0
    ry = math.degrees(float(hp.rotation_xyz[1])) if rot_valid else 0.0
    rz = math.degrees(float(hp.rotation_xyz[2])) if rot_valid else 0.0

    vals = [px, py, pz, rx, ry, rz]
    for i in range(6):
        f = state.features[i]
        f.current_val = vals[i]
        if f.enabled:
            state.client.send_message(f.address, float(vals[i]))


def main():
    try:
        parser = argparse.ArgumentParser(description='Stream Tobii 4C gaze and head pose data to OSC and move mouse cursor')
        parser.add_argument('--no-mouse', action='store_true', help='Disable automatically moving mouse cursor based on gaze X and Y')
        parser.add_argument('--ip', type=str, default=OSC_IP, help=f'OSC Destination IP (default: {OSC_IP})')
        parser.add_argument('--port', type=int, default=OSC_PORT, help=f'OSC Destination Port (default: {OSC_PORT})')
        parser.add_argument('--no-elevate', action='store_true', help='Do not attempt to automatically elevate privileges to Administrator on Windows')
        args, _ = parser.parse_known_args()

        if not args.no_elevate:
            elevate_privileges()

        minimize_console_window()

        if args.no_mouse:
            state.move_mouse = False
        if args.ip or args.port:
            state.client = udp_client.SimpleUDPClient(args.ip, args.port)

        print("Loading Tobii Stream Engine library...")
        raw_lib = load_tobii_stream_engine()

        if not raw_lib:
            print("=" * 72)
            print("ERROR: Could not load 'tobii_stream_engine.dll' (or system equivalent).")
            print("\nTroubleshooting Guidance:")
            print("  1. Check architecture match: Python bitness must match the DLL bitness.")
            print(f"     Current Python process architecture: {struct_calcsize_bits()}-bit")
            print("  2. Ensure Tobii Eye Tracking Service / Stream Engine is installed.")
            print("  3. Check DLL Loader Diagnostic Log printed above for the exact error reason.")
            print("=" * 72)
            if sys.platform == "win32":
                input("\nPress Enter to exit...")
            return

        api = TobiiStreamEngineAPI(raw_lib)

        if not api.tobii_api_create:
            print("ERROR: API functions missing from Tobii Stream Engine library.")
            if sys.platform == "win32":
                input("\nPress Enter to exit...")
            return

        api_ptr = c_void_p()
        res = api.tobii_api_create(ctypes.byref(api_ptr), None, None)
        if res != TOBII_ERROR_NO_ERROR or not api_ptr:
            print(f"ERROR: tobii_api_create failed with status: {api.get_error_str(res)} ({res}).")
            if sys.platform == "win32":
                input("\nPress Enter to exit...")
            return
        state.api_handle = api_ptr

        print("Searching for Tobii eye trackers via Stream Engine...")

        found_urls = []
        def url_receiver(url_c, user_data):
            if url_c:
                found_urls.append(url_c.decode('utf-8'))

        state.c_url_cb = tobii_url_receiver_t(url_receiver)

        if api.tobii_enumerate_local_device_urls:
            api.tobii_enumerate_local_device_urls(state.api_handle, state.c_url_cb, None)

        state.device_urls = found_urls

        if len(state.device_urls) == 0:
            print("No Tobii eye trackers found via Tobii Stream Engine API!")
            print("Ensure Tobii Core software / Eye Tracking Service is running and device is connected.")
            if api.tobii_api_destroy and state.api_handle:
                api.tobii_api_destroy(state.api_handle)
            if sys.platform == "win32":
                input("\nPress Enter to exit...")
            return

        # Prepare persistent callback objects
        state.c_gaze_data_cb = tobii_gaze_data_callback_t(on_gaze_data)
        state.c_gaze_point_cb = tobii_gaze_point_callback_t(on_gaze_point)
        state.c_head_pose_cb = tobii_head_pose_callback_t(on_head_pose)

        def switch_tracker(idx):
            if state.device_handle:
                if api.tobii_gaze_data_unsubscribe:
                    try: api.tobii_gaze_data_unsubscribe(state.device_handle)
                    except Exception: pass
                if api.tobii_gaze_point_unsubscribe:
                    try: api.tobii_gaze_point_unsubscribe(state.device_handle)
                    except Exception: pass
                if api.tobii_head_pose_unsubscribe:
                    try: api.tobii_head_pose_unsubscribe(state.device_handle)
                    except Exception: pass
                if api.tobii_device_destroy:
                    try: api.tobii_device_destroy(state.device_handle)
                    except Exception: pass
                state.device_handle = None

            url = state.device_urls[idx]
            state.current_device_url = url
            dev_ptr = c_void_p()

            ret = api.create_device(state.api_handle, url.encode('utf-8'), dev_ptr)

            if ret != TOBII_ERROR_NO_ERROR or not dev_ptr:
                err_desc = api.get_error_str(ret)
                print(f"Failed to create Tobii device for URL '{url}' ({err_desc}, code: {ret})")
                return False

            state.device_handle = dev_ptr

            # Subscribe gaze data (fallback to gaze point if gaze data not supported)
            gaze_sub = False
            if api.tobii_gaze_data_subscribe:
                r = api.tobii_gaze_data_subscribe(state.device_handle, state.c_gaze_data_cb, None)
                if r == TOBII_ERROR_NO_ERROR:
                    gaze_sub = True
                    print(f"Subscribed to Gaze Data on {url}")

            if not gaze_sub and api.tobii_gaze_point_subscribe:
                r = api.tobii_gaze_point_subscribe(state.device_handle, state.c_gaze_point_cb, None)
                if r == TOBII_ERROR_NO_ERROR:
                    print(f"Subscribed to Gaze Point on {url}")

            # Subscribe head pose
            if api.tobii_head_pose_subscribe:
                r = api.tobii_head_pose_subscribe(state.device_handle, state.c_head_pose_cb, None)
                if r == TOBII_ERROR_NO_ERROR:
                    print(f"Subscribed to Head Pose on {url}")
                else:
                    print(f"Head Pose subscription unavailable or not supported on {url}")

            return True

        if not switch_tracker(0):
            print("Failed to connect to primary Tobii device.")
            if sys.platform == "win32":
                input("\nPress Enter to exit...")
            return

        win_name = 'Tobii 4C OSC (Stream Engine)'
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win_name, 1420, 480)
        cv2.setMouseCallback(win_name, on_mouse)

        # Draw initial frame and minimize GUI window immediately
        initial_img = np.zeros((480, 1420, 3), dtype=np.uint8)
        cv2.imshow(win_name, initial_img)
        cv2.waitKey(1)
        minimize_gui_window(win_name)

        w, h = 640, 480

        print(f"Streaming data to {args.ip}:{args.port}")
        if state.move_mouse:
            print(f"[Mouse Control] Mouse control enabled (SetCursorPos/pynput). Resolution: {state.screen_size[0]}x{state.screen_size[1]}")
        else:
            print("[Mouse Control] Mouse control disabled.")
        print("Press 'm' to toggle mouse control, 'n' to cycle through trackers, ESC to exit.")

        while state.running:
            if api.tobii_device_process_callbacks and state.device_handle:
                api.tobii_device_process_callbacks(state.device_handle)

            tracker_info = f"Tobii Stream Engine: {state.current_device_url or 'Unknown'}"
            mouse_status = f"Mouse Control: {'ON' if state.move_mouse else 'OFF'} ('m' toggle)"
            display_img = np.zeros((h, w, 3), dtype=np.uint8)
            cv2.putText(display_img, tracker_info[:45], (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(display_img, mouse_status, (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0) if state.move_mouse else (0, 0, 255), 1)

            # Draw Gaze Visualization
            if state.last_gaze_data:
                lx, ly = state.last_gaze_data.get('left_gaze_point_on_display_area', (float('nan'), float('nan')))
                rx, ry = state.last_gaze_data.get('right_gaze_point_on_display_area', (float('nan'), float('nan')))

                valid_l = not (math.isnan(lx) or math.isnan(ly))
                valid_r = not (math.isnan(rx) or math.isnan(ry))

                if valid_l:
                    cv2.circle(display_img, (int(lx * w), int(ly * h)), 10, (255, 0, 0), 2)
                if valid_r:
                    cv2.circle(display_img, (int(rx * w), int(ry * h)), 10, (0, 0, 255), 2)

                if valid_l and valid_r:
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
            if key == 27: break  # ESC
            if key == ord('m'):
                state.move_mouse = not state.move_mouse
                state.save_config()
                print(f"[Mouse Control] Toggled mouse control: {'ON' if state.move_mouse else 'OFF'}")
            if key == ord('n') and len(state.device_urls) > 1:  # Cycle trackers
                state.tracker_index = (state.tracker_index + 1) % len(state.device_urls)
                switch_tracker(state.tracker_index)

            time.sleep(0.001)

        # Cleanup device and API
        if state.device_handle:
            if api.tobii_gaze_data_unsubscribe:
                try: api.tobii_gaze_data_unsubscribe(state.device_handle)
                except Exception: pass
            if api.tobii_gaze_point_unsubscribe:
                try: api.tobii_gaze_point_unsubscribe(state.device_handle)
                except Exception: pass
            if api.tobii_head_pose_unsubscribe:
                try: api.tobii_head_pose_unsubscribe(state.device_handle)
                except Exception: pass
            if api.tobii_device_destroy:
                try: api.tobii_device_destroy(state.device_handle)
                except Exception: pass

        if state.api_handle and api.tobii_api_destroy:
            try: api.tobii_api_destroy(state.api_handle)
            except Exception: pass

        cv2.destroyAllWindows()
        print("Successfully unsubscribed and closed Tobii Stream Engine session.")

    except Exception:
        traceback.print_exc()
        if sys.platform == "win32":
            input("\nPress Enter to close...")

def struct_calcsize_bits():
    import struct
    return struct.calcsize("P") * 8

if __name__ == "__main__":
    main()
