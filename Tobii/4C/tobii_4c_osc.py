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
import socket
import threading

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

# Windows SendInput structures for synthetic mouse input injection
if sys.platform == "win32":
    class MOUSEINPUT(Structure):
        _fields_ = [
            ("dx", c_int),
            ("dy", c_int),
            ("mouseData", c_uint32),
            ("dwFlags", c_uint32),
            ("time", c_uint32),
            ("dwExtraInfo", c_void_p),
        ]

    class INPUT_UNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]

    class INPUT(Structure):
        _fields_ = [
            ("type", c_uint32),
            ("union", INPUT_UNION),
        ]

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
TCP_PORT = 10003
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "checkbox_states_tobii.json")

def compute_smoothing(jump_pixels, min_jump=5.0, max_jump=100.0, max_smoothing=0.8, curve_factor=2.0):
    """
    Computes smoothing factor (0.0 to max_smoothing) given a movement jump in pixels.
    Small jumps (0 to min_jump pixels) receive maximum smoothing (max_smoothing).
    As the jump size increases towards max_jump, smoothing decreases towards 0.0 with an exponential curve response.
    """
    if max_jump <= min_jump:
        return 0.0

    if jump_pixels <= min_jump:
        return max(0.0, min(0.999, float(max_smoothing)))

    if jump_pixels >= max_jump:
        return 0.0

    # norm_small_jump goes from 1.0 (at jump_pixels == min_jump) down to 0.0 (at jump_pixels == max_jump)
    norm_small_jump = (max_jump - jump_pixels) / (max_jump - min_jump)
    norm_small_jump = min(1.0, max(0.0, norm_small_jump))

    if abs(curve_factor) < 1e-6:
        factor = norm_small_jump
    elif curve_factor > 0:
        factor = math.pow(norm_small_jump, 1.0 + float(curve_factor))
    else:
        exponent = 1.0 + abs(float(curve_factor))
        factor = 1.0 - math.pow(1.0 - norm_small_jump, exponent)

    smoothing = factor * float(max_smoothing)
    return max(0.0, min(0.999, smoothing))


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
    Sets system mouse cursor position using Windows SendInput API (ctypes),
    SetCursorPos API, or pynput fallback.
    """
    if sys.platform == "win32":
        try:
            INPUT_MOUSE = 0
            MOUSEEVENTF_MOVE = 0x0001
            MOUSEEVENTF_ABSOLUTE = 0x8000

            sw, sh = state.screen_size
            if sw > 1 and sh > 1:
                norm_x = int(round(px * 65535.0 / (sw - 1)))
                norm_y = int(round(py * 65535.0 / (sh - 1)))
                norm_x = max(0, min(65535, norm_x))
                norm_y = max(0, min(65535, norm_y))

                inp = INPUT()
                inp.type = INPUT_MOUSE
                inp.union.mi = MOUSEINPUT(
                    dx=norm_x,
                    dy=norm_y,
                    mouseData=0,
                    dwFlags=MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE,
                    time=0,
                    dwExtraInfo=None
                )
                sent = ctypes.windll.user32.SendInput(1, byref(inp), ctypes.sizeof(INPUT))
                if sent > 0:
                    return True
        except Exception:
            pass

        try:
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
    target_x = max(0.0, min(1.0, float(gx))) * sw
    target_y = max(0.0, min(1.0, float(gy))) * sh

    if state.curr_mouse_x is None or state.curr_mouse_y is None:
        state.curr_mouse_x = target_x
        state.curr_mouse_y = target_y
        state.last_jump_dist = 0.0
        state.last_smoothing = compute_smoothing(
            0.0,
            min_jump=state.smooth_min_jump,
            max_jump=state.smooth_max_jump,
            max_smoothing=state.max_smoothing,
            curve_factor=state.curve_factor
        )
    else:
        dx = target_x - state.curr_mouse_x
        dy = target_y - state.curr_mouse_y
        dist = math.hypot(dx, dy)

        smoothing = compute_smoothing(
            dist,
            min_jump=state.smooth_min_jump,
            max_jump=state.smooth_max_jump,
            max_smoothing=state.max_smoothing,
            curve_factor=state.curve_factor
        )
        state.last_jump_dist = dist
        state.last_smoothing = smoothing

        alpha = 1.0 - smoothing
        state.curr_mouse_x += dx * alpha
        state.curr_mouse_y += dy * alpha

    return set_cursor_pos(state.curr_mouse_x, state.curr_mouse_y)

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
        self.smooth_min_jump = float(self.config.get("smooth_min_jump", 5.0))
        self.smooth_max_jump = float(self.config.get("smooth_max_jump", 100.0))
        self.max_smoothing = float(self.config.get("max_smoothing", 0.8))
        self.curve_factor = float(self.config.get("curve_factor", 2.0))
        self.curr_mouse_x = None
        self.curr_mouse_y = None
        self.last_jump_dist = 0.0
        self.last_smoothing = 0.0
        self.active_slider = None
        self.slider_rects = {}
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
        self.mouse_ui_rect = None
        self.tcp_port = TCP_PORT
        self.tcp_thread = None
        self.tcp_server_socket = None

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
        new_config["smooth_min_jump"] = self.smooth_min_jump
        new_config["smooth_max_jump"] = self.smooth_max_jump
        new_config["max_smoothing"] = self.max_smoothing
        new_config["curve_factor"] = self.curve_factor
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

def update_slider_param(param_name, mouse_x, s_info):
    rel_x = mouse_x - 640  # offset by display_img width
    track_x1 = s_info['track_x1']
    track_w = s_info['track_w']
    val_min = s_info['val_min']
    val_max = s_info['val_max']

    norm = max(0.0, min(1.0, float(rel_x - track_x1) / float(track_w)))
    new_val = val_min + norm * (val_max - val_min)

    if param_name == "curve_factor":
        state.curve_factor = round(new_val, 2)
    elif param_name == "max_smoothing":
        state.max_smoothing = round(new_val, 2)
    elif param_name == "smooth_min_jump":
        state.smooth_min_jump = round(new_val, 1)
        if state.smooth_min_jump >= state.smooth_max_jump:
            state.smooth_max_jump = state.smooth_min_jump + 1.0
    elif param_name == "smooth_max_jump":
        state.smooth_max_jump = round(new_val, 1)
        if state.smooth_max_jump <= state.smooth_min_jump:
            state.smooth_min_jump = max(0.0, state.smooth_max_jump - 1.0)

def on_mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        if state.mouse_ui_rect and state.mouse_ui_rect[0] <= x <= state.mouse_ui_rect[2] and state.mouse_ui_rect[1] <= y <= state.mouse_ui_rect[3]:
            state.move_mouse = not state.move_mouse
            state.save_config()
            print(f"[Mouse Control] Toggled mouse control via UI: {'ON' if state.move_mouse else 'OFF'}")
            return

        rel_x = x - 640
        for param_name, s_info in state.slider_rects.items():
            r = s_info['rect']
            if r[0] <= rel_x <= r[2] and r[1] <= y <= r[3]:
                state.active_slider = param_name
                update_slider_param(param_name, x, s_info)
                return

        for f in state.features:
            if f.ui_rect and f.ui_rect[0] <= x <= f.ui_rect[2] and f.ui_rect[1] <= y <= f.ui_rect[3]:
                f.enabled = not f.enabled
                state.save_config()
                break

    elif event == cv2.EVENT_MOUSEMOVE:
        if state.active_slider and (flags & cv2.EVENT_FLAG_LBUTTON):
            s_info = state.slider_rects.get(state.active_slider)
            if s_info:
                update_slider_param(state.active_slider, x, s_info)

    elif event == cv2.EVENT_LBUTTONUP:
        if state.active_slider:
            state.save_config()
            state.active_slider = None

def render_middle_panel(state, h=480, w=380):
    panel = np.zeros((h, w, 3), dtype=np.uint8)

    # Header
    cv2.putText(panel, "Real-Time Mouse Smoothing", (15, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    # Graph bounding box
    graph_x, graph_y, graph_w, graph_h = 45, 35, 310, 190
    cv2.rectangle(panel, (graph_x, graph_y), (graph_x + graph_w, graph_y + graph_h), (80, 80, 80), 1)

    # Gridlines
    for i in range(1, 5):
        gy = graph_y + graph_h - int((i / 5.0) * graph_h)
        cv2.line(panel, (graph_x, gy), (graph_x + graph_w, gy), (40, 40, 40), 1)
        gx = graph_x + int((i / 5.0) * graph_w)
        cv2.line(panel, (gx, graph_y), (gx, graph_y + graph_h), (40, 40, 40), 1)

    min_j = state.smooth_min_jump
    max_j = max(min_j + 1.0, state.smooth_max_jump)
    max_s = state.max_smoothing
    c_fac = state.curve_factor

    # Min Jump threshold line (vertical dashed/yellow)
    if min_j > 0 and min_j < max_j:
        min_x = graph_x + int((min_j / max_j) * graph_w)
        cv2.line(panel, (min_x, graph_y), (min_x, graph_y + graph_h), (0, 200, 255), 1)

    # Max Smoothing reference line (horizontal cyan)
    max_s_y = graph_y + graph_h - int(max_s * graph_h)
    cv2.line(panel, (graph_x, max_s_y), (graph_x + graph_w, max_s_y), (255, 200, 0), 1)

    # Plot Curve
    pts = []
    num_samples = 100
    for step in range(num_samples + 1):
        jp = (max_j / num_samples) * step
        sm = compute_smoothing(jp, min_j, max_j, max_s, c_fac)
        px = graph_x + int((step / num_samples) * graph_w)
        py = graph_y + graph_h - int((sm / 1.0) * graph_h)
        pts.append((px, py))

    for i in range(len(pts) - 1):
        cv2.line(panel, pts[i], pts[i+1], (0, 255, 200), 2)

    # Axis Labels
    cv2.putText(panel, "0px", (graph_x - 5, graph_y + graph_h + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
    cv2.putText(panel, f"{int(max_j)}px", (graph_x + graph_w - 25, graph_y + graph_h + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
    cv2.putText(panel, "1.0", (15, graph_y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
    cv2.putText(panel, "0.0", (15, graph_y + graph_h), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)

    # Live Real-Time Indicator Dot
    live_dist = state.last_jump_dist
    live_sm = state.last_smoothing
    live_px = graph_x + int(min(1.0, live_dist / max_j) * graph_w)
    live_py = graph_y + graph_h - int(min(1.0, live_sm / 1.0) * graph_h)

    cv2.circle(panel, (live_px, live_py), 5, (0, 0, 255), -1)
    cv2.circle(panel, (live_px, live_py), 8, (0, 255, 255), 1)

    status_txt = f"Jump: {live_dist:.1f}px | Smooth: {live_sm:.2f}"
    cv2.putText(panel, status_txt, (graph_x + 5, graph_y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255), 1)

    # Sliders rendering
    slider_defs = [
        ("curve_factor", f"Curve Severity: {c_fac:+.2f}", c_fac, -5.0, 5.0),
        ("max_smoothing", f"Max Smoothing: {max_s:.2f}", max_s, 0.0, 0.98),
        ("smooth_min_jump", f"Min Jump Threshold: {min_j:.1f} px", min_j, 0.0, 50.0),
        ("smooth_max_jump", f"Max Jump Scale: {max_j:.1f} px", max_j, 10.0, 300.0),
    ]

    sy_start = 255
    sy_step = 52
    track_x1, track_x2 = 25, 355
    track_w = track_x2 - track_x1

    state.slider_rects = {}

    for idx, (param_name, label, val, val_min, val_max) in enumerate(slider_defs):
        sy = sy_start + idx * sy_step
        cv2.putText(panel, label, (track_x1, sy), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)

        track_y = sy + 14
        cv2.line(panel, (track_x1, track_y), (track_x2, track_y), (80, 80, 80), 4)

        norm = max(0.0, min(1.0, (val - val_min) / (val_max - val_min))) if val_max > val_min else 0.0
        handle_x = track_x1 + int(norm * track_w)

        cv2.line(panel, (track_x1, track_y), (handle_x, track_y), (0, 255, 200), 4)
        cv2.circle(panel, (handle_x, track_y), 7, (255, 255, 255), -1)
        cv2.circle(panel, (handle_x, track_y), 8, (0, 255, 200), 1)

        state.slider_rects[param_name] = {
            'rect': [track_x1 - 5, track_y - 10, track_x2 + 5, track_y + 10],
            'val_min': val_min,
            'val_max': val_max,
            'track_x1': track_x1,
            'track_w': track_w
        }

    return panel

def handle_tcp_command(cmd_str):
    cmd = cmd_str.strip().lower()
    if cmd in ("on", "1", "true", "enable", "enabled"):
        state.move_mouse = True
        state.save_config()
        print("[TCP] Mouse control turned ON")
        return "Mouse control: ON\n"
    elif cmd in ("off", "0", "false", "disable", "disabled"):
        state.move_mouse = False
        state.save_config()
        print("[TCP] Mouse control turned OFF")
        return "Mouse control: OFF\n"
    elif cmd in ("toggle", "m", "switch"):
        state.move_mouse = not state.move_mouse
        state.save_config()
        print(f"[TCP] Toggled mouse control: {'ON' if state.move_mouse else 'OFF'}")
        return f"Mouse control: {'ON' if state.move_mouse else 'OFF'}\n"
    elif cmd in ("status", "get"):
        return f"Mouse control: {'ON' if state.move_mouse else 'OFF'}\n"
    elif cmd:
        return f"Unknown command: '{cmd}'. Use 'on', 'off', 'toggle', or 'status'.\n"
    return ""

def start_tcp_server(host, port):
    def tcp_worker():
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server_sock.bind((host, port))
            server_sock.listen(5)
            server_sock.settimeout(1.0)
            state.tcp_server_socket = server_sock
            print(f"[TCP Server] Listening for commands on {host}:{port}")
        except Exception as e:
            print(f"[TCP Server] Failed to bind TCP server on {host}:{port}: {e}")
            return

        while state.running:
            try:
                client_sock, addr = server_sock.accept()
            except socket.timeout:
                continue
            except Exception:
                break

            def client_handler(cs):
                with cs:
                    cs.settimeout(5.0)
                    try:
                        buf = b""
                        while state.running:
                            chunk = cs.recv(1024)
                            if not chunk:
                                break
                            buf += chunk
                            if b"\n" in buf or b"\r" in buf:
                                lines = buf.replace(b"\r\n", b"\n").replace(b"\r", b"\n").split(b"\n")
                                for line in lines[:-1]:
                                    cmd_text = line.decode('utf-8', errors='ignore')
                                    resp = handle_tcp_command(cmd_text)
                                    if resp:
                                        cs.sendall(resp.encode('utf-8'))
                                buf = lines[-1]
                        if buf:
                            cmd_text = buf.decode('utf-8', errors='ignore')
                            resp = handle_tcp_command(cmd_text)
                            if resp:
                                cs.sendall(resp.encode('utf-8'))
                    except Exception:
                        pass

            t = threading.Thread(target=client_handler, args=(client_sock,), daemon=True)
            t.start()

        try:
            server_sock.close()
        except Exception:
            pass

    t = threading.Thread(target=tcp_worker, daemon=True)
    t.start()
    state.tcp_thread = t

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
        parser.add_argument('--tcp-port', type=int, default=TCP_PORT, help=f'TCP Server Listening Port (default: {TCP_PORT})')
        parser.add_argument('--no-elevate', action='store_true', help='Do not attempt to automatically elevate privileges to Administrator on Windows')
        parser.add_argument('--smooth-min-jump', type=float, help='Minimum jump in pixels below which max smoothing applies (default: 5.0)')
        parser.add_argument('--smooth-max-jump', type=float, help='Maximum jump in pixels at which smoothing becomes 0.0 (default: 100.0)')
        parser.add_argument('--max-smoothing', type=float, help='Maximum smoothing factor [0.0, 1.0) applied to small movements (default: 0.8)')
        parser.add_argument('--curve-factor', type=float, help='Exponential curve factor (> 0 for exponential response, default: 2.0)')
        args, _ = parser.parse_known_args()

        if args.smooth_min_jump is not None:
            state.smooth_min_jump = float(args.smooth_min_jump)
        if args.smooth_max_jump is not None:
            state.smooth_max_jump = float(args.smooth_max_jump)
        if args.max_smoothing is not None:
            state.max_smoothing = float(args.max_smoothing)
        if args.curve_factor is not None:
            state.curve_factor = float(args.curve_factor)
        state.save_config()

        if not args.no_elevate:
            elevate_privileges()

        minimize_console_window()

        if args.no_mouse:
            state.move_mouse = False
        if args.ip or args.port:
            state.client = udp_client.SimpleUDPClient(args.ip, args.port)
        state.tcp_port = args.tcp_port

        start_tcp_server("127.0.0.1", state.tcp_port)

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
        cv2.resizeWindow(win_name, 1800, 480)
        cv2.setMouseCallback(win_name, on_mouse)

        # Draw initial frame and minimize GUI window immediately
        initial_img = np.zeros((480, 1800, 3), dtype=np.uint8)
        cv2.imshow(win_name, initial_img)
        cv2.waitKey(1)
        minimize_gui_window(win_name)

        w, h = 640, 480
        middle_w = 380

        print(f"Streaming data to {args.ip}:{args.port}")
        print(f"TCP control server listening on 127.0.0.1:{state.tcp_port}")
        if state.move_mouse:
            print(f"[Mouse Control] Mouse control enabled (SetCursorPos/pynput). Resolution: {state.screen_size[0]}x{screen_size[1] if 'screen_size' in locals() else state.screen_size[1]}")
        else:
            print("[Mouse Control] Mouse control disabled.")
        print("Click the toggle box in the UI or send TCP commands ('on'/'off'/'toggle') to control mouse movement.")
        print("Press 'n' to cycle through trackers, ESC to exit.")

        while state.running:
            if api.tobii_device_process_callbacks and state.device_handle:
                api.tobii_device_process_callbacks(state.device_handle)

            tracker_info = f"Tobii Stream Engine: {state.current_device_url or 'Unknown'}"
            mouse_status = f"Mouse control: {'ON' if state.move_mouse else 'OFF'}"
            display_img = np.zeros((h, w, 3), dtype=np.uint8)
            cv2.putText(display_img, tracker_info[:45], (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Manual Toggle Button right before "Mouse control: On/Off"
            btn_x, btn_y, btn_size = 10, 43, 12
            cv2.rectangle(display_img, (btn_x, btn_y), (btn_x + btn_size, btn_y + btn_size), (255, 255, 255), 1)
            if state.move_mouse:
                cv2.rectangle(display_img, (btn_x + 2, btn_y + 2), (btn_x + btn_size - 2, btn_y + btn_size - 2), (0, 255, 0), -1)
            state.mouse_ui_rect = [btn_x, btn_y, btn_x + btn_size + 150, btn_y + btn_size]

            cv2.putText(display_img, mouse_status, (btn_x + btn_size + 8, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0) if state.move_mouse else (0, 0, 255), 1)

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

            # --- Rendering Middle Panel ---
            middle_panel = render_middle_panel(state, h=h, w=middle_w)

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

                f.ui_rect = [w + middle_w + tx, ty-cb_size, w + middle_w + tx + sidebar_col_w, ty+5]
                cv2.putText(sidebar, f.name[:20], (tx+15, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

                # Bar visualization
                bar_max_w = sidebar_col_w - 130
                val_norm = min(1.0, abs(f.current_val / f.max_v)) if f.max_v != 0 else 0
                bar_w = int(val_norm * bar_max_w)
                color = (255,100,100) if "Pose" in f.name else (0,255,0)
                cv2.rectangle(sidebar, (tx+120, ty-8), (tx+120+bar_w, ty), color, -1)

            cv2.imshow(win_name, np.hstack((display_img, middle_panel, sidebar)))
            key = cv2.waitKey(5) & 0xFF
            if key == 27: break  # ESC
            if key == ord('n') and len(state.device_urls) > 1:  # Cycle trackers
                state.tracker_index = (state.tracker_index + 1) % len(state.device_urls)
                switch_tracker(state.tracker_index)

            time.sleep(0.001)

        state.running = False

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
